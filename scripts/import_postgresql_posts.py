"""Import a caller-supplied PostgreSQL result set into the product schema.

The query and column mapping are runtime inputs, so this public adapter contains
no source-organization or source-table identifiers. It preserves raw HTML in
``source_post``, persists normalized content artifacts, and rebuilds lineage.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import asyncpg

# Support the documented ``python scripts/import_postgresql_posts.py`` form
# without requiring an editable install of the repository package.
REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from backend.app.lineage_ingestion import rebuild_lineage
from lineageweave.embedding_client import orchestrator_embedding_client
from lineageweave.image_content import orchestrator_vision_client
from lineageweave.post_content_persistence import persist_post_content


SOURCE_NAMESPACE = uuid.UUID("b6e4b1d6-5fd0-4ca1-92b0-8f7a4e2df83e")


@dataclass(frozen=True)
class ColumnMapping:
    """Names returned by the caller's source query."""

    record_key: str
    title: str
    body: str
    created_at: str
    updated_at: str | None
    voc_type: str | None
    visibility: str | None
    stage: str | None
    detail_state: str | None
    draft: str | None
    deleted: str | None
    author_code: str | None
    author_name: str | None
    company_code: str | None
    source_business_unit: str | None
    # The source sales-pool column is optional and must not be mapped from a
    # PU field such as voc_pucode without an authoritative source definition.
    sales_pool: str | None
    customer_code: str | None
    project_code: str | None
    thread_group: str | None
    secondary_group: str | None


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-dsn", required=True)
    parser.add_argument("--target-dsn", required=True)
    parser.add_argument("--query-file", type=Path, required=True)
    parser.add_argument("--source-system-code", required=True)
    parser.add_argument("--record-key-column", required=True)
    parser.add_argument("--title-column", required=True)
    parser.add_argument("--body-column", required=True)
    parser.add_argument("--created-at-column", required=True)
    parser.add_argument("--updated-at-column")
    parser.add_argument("--voc-type-column")
    parser.add_argument("--visibility-column")
    parser.add_argument("--stage-column")
    parser.add_argument("--detail-state-column")
    parser.add_argument("--draft-column")
    parser.add_argument("--deleted-column")
    parser.add_argument(
        "--exclude-draft-value",
        action="append",
        default=[],
        help="authoritative source draft value to skip; repeat for multiple values",
    )
    parser.add_argument(
        "--exclude-deleted-value",
        action="append",
        default=[],
        help="authoritative source deletion value to skip; repeat for multiple values",
    )
    parser.add_argument("--source-author-code-column")
    parser.add_argument("--source-author-name-column")
    parser.add_argument("--source-company-code-column")
    parser.add_argument(
        "--source-business-unit-column",
        "--source-process-unit-column",
        dest="source_business_unit_column",
    )
    parser.add_argument("--source-sales-pool-column")
    parser.add_argument("--source-customer-code-column")
    parser.add_argument("--source-project-code-column")
    parser.add_argument("--thread-group-column")
    parser.add_argument("--secondary-group-column")
    parser.add_argument("--author-subject-id", required=True)
    parser.add_argument("--corporate-entity-code", required=True)
    parser.add_argument("--corporate-entity-name")
    parser.add_argument("--process-unit-code", required=True)
    parser.add_argument("--process-unit-name")
    parser.add_argument(
        "--embedding-model",
        default=os.environ.get("LLM_GATEWAY_EMBEDDING_MODEL", os.environ.get("EMBEDDING_MODEL", "")),
    )
    return parser


def _value(row: Any, column: str | None, default: Any = None) -> Any:
    """Read an optional mapped field without guessing absent source data."""
    if column is None:
        return default
    if column not in row.keys():
        raise KeyError(f"source query did not return mapped column {column!r}")
    return row[column]


def _timestamp(value: Any) -> datetime:
    """Normalize a source timestamp for asyncpg timestamptz parameters."""
    if not isinstance(value, datetime):
        raise TypeError("created/updated source values must be datetime instances")
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value


def _source_code_matches(
    row: Any,
    column: str | None,
    excluded_values: list[str],
) -> bool:
    """Match only caller-supplied source codes, never guessed lifecycle labels."""
    if column is None or not excluded_values:
        return False
    value = _value(row, column)
    if value is None:
        return False
    normalized = str(value).strip().casefold()
    return normalized in {item.strip().casefold() for item in excluded_values}


async def _ensure_scope(conn: asyncpg.Connection, args: argparse.Namespace) -> tuple[str, str, str]:
    """Resolve the existing target account, company, and process unit."""
    account_id = await conn.fetchval(
        "select user_account_id from user_account where external_subject_id = $1",
        args.author_subject_id,
    )
    if account_id is None:
        raise RuntimeError("target account is not seeded; create the real Keyverse account first")
    corporate_id = await conn.fetchval(
        "select corporate_entity_id from corporate_entity where corporate_entity_code = $1",
        args.corporate_entity_code,
    )
    if corporate_id is None:
        corporate_id = await conn.fetchval(
            """
            insert into corporate_entity (corporate_entity_code, entity_name, entity_level_code)
            values ($1, $2, 'company') returning corporate_entity_id
            """,
            args.corporate_entity_code,
            args.corporate_entity_name or args.corporate_entity_code,
        )
    process_unit_id = await conn.fetchval(
        "select process_unit_id from process_unit where process_unit_code = $1 and corporate_entity_id = $2",
        args.process_unit_code,
        corporate_id,
    )
    if process_unit_id is None:
        process_unit_id = await conn.fetchval(
            """
            insert into process_unit (corporate_entity_id, process_unit_code, process_unit_name)
            values ($1, $2, $3) returning process_unit_id
            """,
            corporate_id,
            args.process_unit_code,
            args.process_unit_name or args.process_unit_code,
        )
    await conn.execute(
        "insert into account_affiliation (user_account_id, corporate_entity_id, process_unit_id) values ($1, $2, $3) on conflict do nothing",
        account_id,
        corporate_id,
        process_unit_id,
    )
    return str(account_id), str(corporate_id), str(process_unit_id)


async def import_rows(args: argparse.Namespace) -> dict[str, int]:
    """Import rows and return aggregate evidence only."""
    mapping = ColumnMapping(
        record_key=args.record_key_column,
        title=args.title_column,
        body=args.body_column,
        created_at=args.created_at_column,
        updated_at=args.updated_at_column,
        voc_type=args.voc_type_column,
        visibility=args.visibility_column,
        stage=args.stage_column,
        detail_state=args.detail_state_column,
        draft=args.draft_column,
        deleted=args.deleted_column,
        author_code=args.source_author_code_column,
        author_name=args.source_author_name_column,
        company_code=args.source_company_code_column,
        source_business_unit=args.source_business_unit_column,
        sales_pool=args.source_sales_pool_column,
        customer_code=args.source_customer_code_column,
        project_code=args.source_project_code_column,
        thread_group=args.thread_group_column,
        secondary_group=args.secondary_group_column,
    )
    query = args.query_file.read_text(encoding="utf-8")
    source = await asyncpg.connect(args.source_dsn)
    target = await asyncpg.connect(args.target_dsn)
    imported = 0
    skipped = 0
    try:
        account_id, corporate_id, process_unit_id = await _ensure_scope(target, args)
        rows = await source.fetch(query)
        vision_client = orchestrator_vision_client(
            os.environ.get("ORCHESTRATOR_BASE_URL", ""),
            os.environ.get("ORCHESTRATOR_API_KEY", ""),
            os.environ.get("VISION_MODEL", ""),
        )
        embedding_client = orchestrator_embedding_client(
            os.environ.get("ORCHESTRATOR_BASE_URL", ""),
            os.environ.get("ORCHESTRATOR_API_KEY", ""),
            args.embedding_model,
        )
        for row in rows:
            if _source_code_matches(row, mapping.draft, args.exclude_draft_value) or _source_code_matches(
                row, mapping.deleted, args.exclude_deleted_value
            ):
                skipped += 1
                continue
            record_key = str(_value(row, mapping.record_key)).strip()
            if not record_key:
                raise ValueError("source record key cannot be empty")
            created_at = _timestamp(_value(row, mapping.created_at))
            updated_at = _timestamp(_value(row, mapping.updated_at, created_at))
            post_id = uuid.uuid5(SOURCE_NAMESPACE, f"{args.source_system_code}:{record_key}")
            title = str(_value(row, mapping.title, "") or "")
            body = str(_value(row, mapping.body, "") or "")
            if not body.strip():
                raise ValueError("source post body cannot be empty; import the source record body")
            await target.execute(
                """
                insert into source_post
                    (post_id, author_account_id, corporate_entity_id, process_unit_id,
                     post_title, post_body, voc_type_code, visibility_code,
                     source_stage_code, source_detail_state_code,
                     source_draft_code, source_deleted_flag,
                     source_author_code, source_author_name, source_company_code,
                     source_process_unit_code, source_sales_pool_code,
                     source_customer_code, source_project_code,
                     source_system_code, source_record_key,
                     thread_group_key, secondary_grouping_key, created_at, updated_at)
                values ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17, $18, $19, $20, $21, $22, $23, $24, $25)
                on conflict (post_id) do update set
                    author_account_id = excluded.author_account_id,
                    corporate_entity_id = excluded.corporate_entity_id,
                    process_unit_id = excluded.process_unit_id,
                    post_title = excluded.post_title,
                    post_body = excluded.post_body,
                    voc_type_code = excluded.voc_type_code,
                    visibility_code = excluded.visibility_code,
                    source_stage_code = excluded.source_stage_code,
                    source_detail_state_code = excluded.source_detail_state_code,
                    source_draft_code = excluded.source_draft_code,
                    source_deleted_flag = excluded.source_deleted_flag,
                    source_author_code = excluded.source_author_code,
                    source_author_name = excluded.source_author_name,
                    source_company_code = excluded.source_company_code,
                    source_process_unit_code = excluded.source_process_unit_code,
                    source_sales_pool_code = excluded.source_sales_pool_code,
                    source_customer_code = excluded.source_customer_code,
                    source_project_code = excluded.source_project_code,
                    source_system_code = excluded.source_system_code,
                    source_record_key = excluded.source_record_key,
                    thread_group_key = excluded.thread_group_key,
                    secondary_grouping_key = excluded.secondary_grouping_key,
                    created_at = excluded.created_at,
                    updated_at = excluded.updated_at
                """,
                post_id,
                account_id,
                corporate_id,
                process_unit_id,
                title,
                body,
                str(_value(row, mapping.voc_type, "voc") or "voc"),
                str(_value(row, mapping.visibility, "public") or "public"),
                str(_value(row, mapping.stage) or "").strip() or None,
                str(_value(row, mapping.detail_state) or "").strip() or None,
                str(_value(row, mapping.draft) or "").strip() or None,
                str(_value(row, mapping.deleted) or "").strip() or None,
                str(_value(row, mapping.author_code) or "").strip() or None,
                str(_value(row, mapping.author_name) or "").strip() or None,
                str(_value(row, mapping.company_code) or "").strip() or None,
                str(_value(row, mapping.source_business_unit) or "").strip() or None,
                str(_value(row, mapping.sales_pool) or "").strip() or None,
                str(_value(row, mapping.customer_code) or "").strip() or None,
                str(_value(row, mapping.project_code) or "").strip() or None,
                args.source_system_code,
                record_key,
                str(_value(row, mapping.thread_group, args.process_unit_code) or args.process_unit_code),
                str(_value(row, mapping.secondary_group, "") or ""),
                created_at,
                updated_at,
            )
            await target.execute(
                """
                insert into source_post_revision (post_id, post_title, post_body, written_at, superseded_at)
                select $1, $2, $3, $4, null
                where not exists (
                    select 1 from source_post_revision
                    where post_id = $1 and written_at = $4 and superseded_at is null
                )
                """,
                post_id,
                title,
                body,
                updated_at,
            )
            await persist_post_content(
                target,
                str(post_id),
                body,
                vision_client=vision_client,
                embedding_client=embedding_client,
                embedding_model_code=args.embedding_model or None,
            )
            imported += 1
        edges = await rebuild_lineage(target)
        return {
            "source_rows": len(rows),
            "imported_rows": imported,
            "skipped_rows": skipped,
            "lineage_edges": len(edges),
        }
    finally:
        await source.close()
        await target.close()


def main() -> None:
    """Run the private, caller-mapped import and print aggregate evidence."""
    args = _parser().parse_args()
    print(json.dumps(asyncio.run(import_rows(args)), sort_keys=True))


if __name__ == "__main__":
    main()
