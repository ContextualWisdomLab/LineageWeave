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
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import asyncpg

# Support the documented ``python scripts/import_postgresql_posts.py`` form
# without requiring an editable install of the repository package.
REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from backend.app.lineage_ingestion import ChannelWeightsNotEstimated, rebuild_lineage
from lineageweave.adjudication_client import (
    ContextualOrchestratorAdjudicationClient,
    NullAdjudicationClient,
)
from lineageweave.embedding_client import orchestrator_embedding_client
from lineageweave.image_content import orchestrator_vision_client
from lineageweave.llm_context import build_post_llm_metadata, use_llm_metadata
from lineageweave.post_content_persistence import persist_post_content
from lineageweave.post_structure import (
    ContextualOrchestratorPostStructureClient,
    NullPostStructureClient,
)
from lineageweave.synthetic_seed_cleanup import cleanup_synthetic_seed

SOURCE_NAMESPACE = uuid.UUID("b6e4b1d6-5fd0-4ca1-92b0-8f7a4e2df83e")

_VOC_TYPE_ALIASES = {
    "voc": "voc",
    "vocc": "vocc",
    "voco": "voco",
    "vom": "vom",
    "vop": "vop",
}


def _normalize_voc_type(value: Any) -> str:
    """Preserve the governed source VOC vocabulary as canonical target codes."""
    if value is None or not str(value).strip():
        raise ValueError("mapped source VOC type is empty")
    normalized = _VOC_TYPE_ALIASES.get(str(value).strip().casefold())
    if normalized is None:
        raise ValueError(f"unsupported source VOC type {value!r}")
    return normalized


@dataclass(frozen=True)
class ColumnMapping:
    """Names returned by the caller's source query."""

    record_key: str
    post_id: str | None
    title: str
    body: str | None
    created_at: str
    updated_at: str | None
    event_occurred_at: str | None
    voc_type: str | None
    visibility: str | None
    stage: str | None
    detail_state: str | None
    draft: str | None
    deleted: str | None
    author_code: str | None
    author_name: str | None
    company_code: str | None
    company_name: str | None
    source_business_unit: str | None
    source_business_unit_name: str | None
    # The source sales-pool column is optional and must not be mapped from a
    # PU field such as voc_pucode without an authoritative source definition.
    sales_pool: str | None
    sales_pool_name: str | None
    customer_code: str | None
    customer_name: str | None
    project_code: str | None
    project_name: str | None
    thread_group: str | None
    secondary_group: str | None


def _parser() -> argparse.ArgumentParser:
    """Build the explicit caller-mapped import command contract."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-dsn", required=True)
    parser.add_argument("--target-dsn", required=True)
    parser.add_argument("--query-file", type=Path, required=True)
    parser.add_argument("--source-system-code", required=True)
    parser.add_argument("--record-key-column", required=True)
    parser.add_argument(
        "--post-id-column",
        help="optional source UUID column for post_id; otherwise derive it from record key",
    )
    parser.add_argument("--title-column", required=True)
    body_group = parser.add_mutually_exclusive_group(required=True)
    body_group.add_argument("--body-column")
    body_group.add_argument(
        "--no-body-dimension-evidence",
        default="",
        help=(
            "written evidence that the source export has no body dimension; "
            "the title remains a title and no semantic body is invented"
        ),
    )
    parser.add_argument("--created-at-column", required=True)
    parser.add_argument("--updated-at-column")
    parser.add_argument(
        "--event-occurred-at-column",
        help="optional source-system event instant; Global Ask falls back to created_at when omitted",
    )
    parser.add_argument("--voc-type-column", required=True)
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
    parser.add_argument(
        "--no-draft-dimension-evidence",
        default="",
        help=(
            "written evidence that this export has no authorship-draft "
            "dimension at all (mutually exclusive with --draft-column); "
            "surfaced verbatim in the import summary for audit"
        ),
    )
    parser.add_argument("--source-author-code-column")
    parser.add_argument("--source-author-name-column")
    parser.add_argument("--source-company-code-column")
    parser.add_argument("--source-company-name-column")
    parser.add_argument(
        "--source-business-unit-column",
        "--source-process-unit-column",
        dest="source_business_unit_column",
    )
    parser.add_argument(
        "--source-business-unit-name-column",
        "--source-process-unit-name-column",
        dest="source_business_unit_name_column",
    )
    parser.add_argument("--source-sales-pool-column")
    parser.add_argument("--source-sales-pool-name-column")
    parser.add_argument("--source-customer-code-column")
    parser.add_argument("--source-customer-name-column")
    parser.add_argument("--source-project-code-column")
    parser.add_argument("--source-project-name-column")
    parser.add_argument("--thread-group-column")
    parser.add_argument("--secondary-group-column")
    parser.add_argument("--author-subject-id", required=True)
    parser.add_argument("--corporate-entity-code", required=True)
    parser.add_argument(
        "--allow-demo-corporate-entity",
        action="store_true",
        help="explicitly allow the synthetic DEMO-* scope for a test import",
    )
    parser.add_argument("--corporate-entity-name")
    parser.add_argument("--process-unit-code", required=True)
    parser.add_argument("--process-unit-name")
    return parser


def _validate_corporate_entity_scope(code: str, *, allow_demo: bool) -> None:
    """Prevent real imports from silently sharing the synthetic Demo scope."""
    normalized = code.strip()
    if not normalized:
        raise ValueError("corporate entity code cannot be empty")
    if normalized.startswith("DEMO-") and not allow_demo:
        raise ValueError(
            "real imports must use a non-DEMO corporate entity code; "
            "use --allow-demo-corporate-entity only for an explicit synthetic test"
        )


def _value(row: Any, column: str | None, default: Any = None) -> Any:
    """Read an optional mapped field without guessing absent source data."""
    if column is None:
        return default
    if column not in row:
        raise KeyError(f"source query did not return mapped column {column!r}")
    return row[column]


def _source_post_id(row: Any, mapping: ColumnMapping, source_system_code: str, record_key: str) -> uuid.UUID:
    """Keep a source UUID independent from the human-entered source record key."""
    if mapping.post_id is None:
        return uuid.uuid5(SOURCE_NAMESPACE, f"{source_system_code}:{record_key}")
    raw_post_id = str(_value(row, mapping.post_id, "") or "").strip()
    if not raw_post_id:
        raise ValueError(f"source post id cannot be empty in mapped column {mapping.post_id!r}")
    try:
        return uuid.UUID(raw_post_id)
    except ValueError as exc:
        raise ValueError(f"source post id is not a UUID: {raw_post_id!r}") from exc


def _timestamp(value: Any) -> datetime:
    """Normalize a source timestamp for asyncpg timestamptz parameters."""
    if not isinstance(value, datetime):
        raise TypeError("created/updated source values must be datetime instances")
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value


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


def _lineage_grouping_values(
    row: Any,
    mapping: ColumnMapping,
    *,
    record_key: str,
    default_group: str,
) -> tuple[str | None, str | None, str, str]:
    """Return raw source grouping followed by reconstruction grouping.

    A source thread key equal to its own record key is row identity, not
    grouping evidence. Preserve both raw fields for provenance while deriving
    the documented empty-thread/project-key reconstruction inputs.
    """
    source_thread = str(_value(row, mapping.thread_group) or "").strip() or None
    source_secondary = str(_value(row, mapping.secondary_group) or "").strip() or None
    if source_thread == record_key:
        project = str(_value(row, mapping.project_code) or "").strip()
        return source_thread, source_secondary, "", project
    return (
        source_thread,
        source_secondary,
        source_thread or default_group,
        source_secondary or "",
    )


def _validate_source_mapping(
    sales_pool_column: str | None,
    process_unit_column: str | None,
) -> None:
    """Reject the common PU-to-sales-pool mapping error at the import boundary."""
    if sales_pool_column and process_unit_column and sales_pool_column == process_unit_column:
        raise ValueError(
            "source sales pool and PU/business-unit columns must be distinct; "
            "PU is source_process_unit_code, not source_sales_pool_code"
        )


def _validate_publication_state(
    rows: list[Any],
    mapping: ColumnMapping,
    excluded_draft_values: list[str],
    no_draft_dimension_evidence: str = "",
) -> None:
    """Require evidence that imported rows have a known publication state.

    Two doors, both explicit: either a mapped draft column with excluded
    values, or ``--no-draft-dimension-evidence`` carrying the operator's
    written evidence that the export has no authorship-draft dimension
    at all (e.g. every candidate draft column is NULL across the export
    and a prior full-corpus pipeline treated every lifecycle stage as a
    real document). The evidence note is surfaced in the import summary
    so the claim is auditable, never implicit.
    """
    evidence = no_draft_dimension_evidence.strip()
    if evidence:
        if mapping.draft is not None or excluded_draft_values:
            raise ValueError(
                "--no-draft-dimension-evidence cannot be combined with a "
                "mapped draft column or --exclude-draft-value; pick one "
                "publication-state door"
            )
        return
    if mapping.draft is None:
        raise ValueError("source draft status column is required for publication-state preflight")
    if not excluded_draft_values:
        raise ValueError("at least one source draft value must be excluded explicitly")
    if rows and not any(str(_value(row, mapping.draft) or "").strip() for row in rows):
        raise ValueError("source publication state is unknown: draft status has no values")


def _validate_source_rows(
    rows: list[Any],
    mapping: ColumnMapping,
    excluded_draft_values: list[str],
    excluded_deleted_values: list[str],
    no_draft_dimension_evidence: str = "",
    no_body_dimension_evidence: str = "",
) -> None:
    """Reject incomplete source evidence before the target is mutated."""
    _validate_publication_state(
        rows, mapping, excluded_draft_values, no_draft_dimension_evidence
    )
    body_evidence = no_body_dimension_evidence.strip()
    if mapping.body is None:
        if not body_evidence:
            raise ValueError(
                "--no-body-dimension-evidence requires an operator evidence statement"
            )
    elif body_evidence:
        raise ValueError(
            "--no-body-dimension-evidence cannot be combined with a mapped body column"
        )
    seen_record_keys: dict[str, int] = {}
    seen_post_ids: dict[uuid.UUID, int] = {}
    post_id_column = getattr(mapping, "post_id", None)
    for row_number, row in enumerate(rows, start=1):
        if _source_code_matches(row, mapping.draft, excluded_draft_values) or _source_code_matches(
            row, mapping.deleted, excluded_deleted_values
        ):
            continue
        record_key = str(_value(row, mapping.record_key) or "").strip()
        if not record_key:
            raise ValueError(f"source record key cannot be empty at source row {row_number}")
        if post_id_column is None:
            previous_row = seen_record_keys.get(record_key)
            if previous_row is not None:
                raise ValueError(
                    f"duplicate source record key at source rows {previous_row} and {row_number}"
                )
            seen_record_keys[record_key] = row_number
        else:
            post_id = _source_post_id(row, mapping, "validation", record_key)
            previous_row = seen_post_ids.get(post_id)
            if previous_row is not None:
                raise ValueError(
                    f"duplicate source post id at source rows {previous_row} and {row_number}"
                )
            seen_post_ids[post_id] = row_number
        body = str(_value(row, mapping.body) or "")
        if mapping.body is not None and not body.strip():
            raise ValueError(f"source post body cannot be empty at source row {row_number}")
        voc_type_column = getattr(mapping, "voc_type", None)
        if voc_type_column is None:
            raise ValueError("source VOC type column is required")
        try:
            _normalize_voc_type(_value(row, voc_type_column))
        except ValueError as exc:
            raise ValueError(f"invalid source VOC type at source row {row_number}: {exc}") from exc


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


async def import_rows(args: argparse.Namespace) -> dict[str, object]:
    """Import rows and return aggregate evidence only."""
    _validate_corporate_entity_scope(
        args.corporate_entity_code,
        allow_demo=args.allow_demo_corporate_entity,
    )
    mapping = ColumnMapping(
        record_key=args.record_key_column,
        post_id=args.post_id_column,
        title=args.title_column,
        body=args.body_column,
        created_at=args.created_at_column,
        updated_at=args.updated_at_column,
        event_occurred_at=args.event_occurred_at_column,
        voc_type=args.voc_type_column,
        visibility=args.visibility_column,
        stage=args.stage_column,
        detail_state=args.detail_state_column,
        draft=args.draft_column,
        deleted=args.deleted_column,
        author_code=args.source_author_code_column,
        author_name=args.source_author_name_column,
        company_code=args.source_company_code_column,
        company_name=args.source_company_name_column,
        source_business_unit=args.source_business_unit_column,
        source_business_unit_name=args.source_business_unit_name_column,
        sales_pool=args.source_sales_pool_column,
        sales_pool_name=args.source_sales_pool_name_column,
        customer_code=args.source_customer_code_column,
        customer_name=args.source_customer_name_column,
        project_code=args.source_project_code_column,
        project_name=args.source_project_name_column,
        thread_group=args.thread_group_column,
        secondary_group=args.secondary_group_column,
    )
    _validate_source_mapping(mapping.sales_pool, mapping.source_business_unit)
    query = args.query_file.read_text(encoding="utf-8")
    source = await asyncpg.connect(args.source_dsn)
    target = await asyncpg.connect(args.target_dsn)
    imported = 0
    skipped = 0
    try:
        rows = await source.fetch(query)
        _validate_source_rows(
            rows,
            mapping,
            args.exclude_draft_value,
            args.exclude_deleted_value,
            args.no_draft_dimension_evidence,
            args.no_body_dimension_evidence,
        )
        account_id, corporate_id, process_unit_id = await _ensure_scope(target, args)
        vision_client = orchestrator_vision_client(
            os.environ.get("ORCHESTRATOR_BASE_URL", ""),
            os.environ.get("ORCHESTRATOR_API_KEY", ""),
        )
        embedding_client = orchestrator_embedding_client(
            os.environ.get("ORCHESTRATOR_BASE_URL", ""),
            os.environ.get("ORCHESTRATOR_API_KEY", ""),
        )
        orchestrator_base_url = os.environ.get("ORCHESTRATOR_BASE_URL", "")
        orchestrator_api_key = os.environ.get("ORCHESTRATOR_API_KEY", "")
        structure_client = (
            ContextualOrchestratorPostStructureClient(orchestrator_base_url, orchestrator_api_key)
            if orchestrator_base_url and orchestrator_api_key
            else NullPostStructureClient()
        )
        adjudication_client = (
            ContextualOrchestratorAdjudicationClient(
                orchestrator_base_url,
                orchestrator_api_key,
            )
            if orchestrator_base_url and orchestrator_api_key
            else NullAdjudicationClient()
        )
        for row in rows:
            if _source_code_matches(row, mapping.draft, args.exclude_draft_value) or _source_code_matches(
                row, mapping.deleted, args.exclude_deleted_value
            ):
                skipped += 1
                continue
            record_key = str(_value(row, mapping.record_key)).strip()
            created_at = _timestamp(_value(row, mapping.created_at))
            # A mapped updated column that is NULL means "never updated",
            # not missing evidence: fall back to created_at instead of
            # rejecting the row.
            raw_updated_at = _value(row, mapping.updated_at, created_at)
            updated_at = (
                created_at if raw_updated_at is None else _timestamp(raw_updated_at)
            )
            event_raw = (
                _value(row, mapping.event_occurred_at) if mapping.event_occurred_at else None
            )
            event_occurred_at = _timestamp(event_raw) if event_raw is not None else None
            post_id = _source_post_id(row, mapping, args.source_system_code, record_key)
            title = str(_value(row, mapping.title, "") or "")
            body = str(_value(row, mapping.body, "") or "")
            voc_type_code = _normalize_voc_type(_value(row, mapping.voc_type))
            (
                source_thread_group_key,
                source_secondary_grouping_key,
                thread_group_key,
                secondary_grouping_key,
            ) = _lineage_grouping_values(
                row,
                mapping,
                record_key=record_key,
                default_group=args.process_unit_code,
            )
            preserve_existing_body = mapping.body is None
            effective_body = await target.fetchval(
                """
                insert into source_post
                    (post_id, author_account_id, corporate_entity_id, process_unit_id,
                     post_title, post_body, voc_type_code, visibility_code,
                     source_stage_code, source_detail_state_code,
                     source_draft_code, source_deleted_flag,
                     source_author_code, source_author_name, source_company_code, source_company_name,
                     source_process_unit_code, source_process_unit_name,
                     source_sales_pool_code, source_sales_pool_name,
                     source_customer_code, source_customer_name,
                     source_project_code, source_project_name,
                     source_system_code, source_record_key,
                     source_thread_group_key, source_secondary_grouping_key,
                     thread_group_key, secondary_grouping_key, created_at, updated_at,
                     event_occurred_at)
                values ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17, $18, $19, $20, $21, $22, $23, $24, $25, $26, $27, $28, $29, $30, $31, $32, $33)
                on conflict (post_id) do update set
                    author_account_id = excluded.author_account_id,
                    corporate_entity_id = excluded.corporate_entity_id,
                    process_unit_id = excluded.process_unit_id,
                    post_title = excluded.post_title,
                    post_body = case
                        when $34 then source_post.post_body
                        else excluded.post_body
                    end,
                    voc_type_code = excluded.voc_type_code,
                    visibility_code = excluded.visibility_code,
                    source_stage_code = excluded.source_stage_code,
                    source_detail_state_code = excluded.source_detail_state_code,
                    source_draft_code = excluded.source_draft_code,
                    source_deleted_flag = excluded.source_deleted_flag,
                    source_author_code = excluded.source_author_code,
                    source_author_name = excluded.source_author_name,
                    source_company_code = excluded.source_company_code,
                    source_company_name = excluded.source_company_name,
                    source_process_unit_code = excluded.source_process_unit_code,
                    source_process_unit_name = excluded.source_process_unit_name,
                    source_sales_pool_code = excluded.source_sales_pool_code,
                    source_sales_pool_name = excluded.source_sales_pool_name,
                    source_customer_code = excluded.source_customer_code,
                    source_customer_name = excluded.source_customer_name,
                    source_project_code = excluded.source_project_code,
                    source_project_name = excluded.source_project_name,
                    source_system_code = excluded.source_system_code,
                    source_record_key = excluded.source_record_key,
                    source_thread_group_key = excluded.source_thread_group_key,
                    source_secondary_grouping_key =
                        excluded.source_secondary_grouping_key,
                    thread_group_key = excluded.thread_group_key,
                    secondary_grouping_key = excluded.secondary_grouping_key,
                    created_at = excluded.created_at,
                    updated_at = excluded.updated_at,
                    event_occurred_at = excluded.event_occurred_at
                returning post_body
                """,
                post_id,
                account_id,
                corporate_id,
                process_unit_id,
                title,
                body,
                voc_type_code,
                str(_value(row, mapping.visibility, "public") or "public"),
                str(_value(row, mapping.stage) or "").strip() or None,
                str(_value(row, mapping.detail_state) or "").strip() or None,
                str(_value(row, mapping.draft) or "").strip() or None,
                str(_value(row, mapping.deleted) or "").strip() or None,
                str(_value(row, mapping.author_code) or "").strip() or None,
                str(_value(row, mapping.author_name) or "").strip() or None,
                str(_value(row, mapping.company_code) or "").strip() or None,
                str(_value(row, mapping.company_name) or "").strip() or None,
                str(_value(row, mapping.source_business_unit) or "").strip() or None,
                str(_value(row, mapping.source_business_unit_name) or "").strip() or None,
                str(_value(row, mapping.sales_pool) or "").strip() or None,
                str(_value(row, mapping.sales_pool_name) or "").strip() or None,
                str(_value(row, mapping.customer_code) or "").strip() or None,
                str(_value(row, mapping.customer_name) or "").strip() or None,
                str(_value(row, mapping.project_code) or "").strip() or None,
                str(_value(row, mapping.project_name) or "").strip() or None,
                args.source_system_code,
                record_key,
                source_thread_group_key,
                source_secondary_grouping_key,
                thread_group_key,
                secondary_grouping_key,
                created_at,
                updated_at,
                event_occurred_at,
                preserve_existing_body,
            )
            if not preserve_existing_body:
                metadata = build_post_llm_metadata(
                    str(post_id),
                    {
                        "author_account_id": account_id,
                        "source_process_unit_code": _value(row, mapping.source_business_unit),
                        "source_author_code": _value(row, mapping.author_code),
                        "source_company_code": _value(row, mapping.company_code),
                        "source_customer_code": _value(row, mapping.customer_code),
                        "source_project_code": _value(row, mapping.project_code),
                        "source_sales_pool_code": _value(row, mapping.sales_pool),
                    },
                )
                with use_llm_metadata(metadata):
                    await persist_post_content(
                        target,
                        str(post_id),
                        effective_body,
                        vision_client=vision_client,
                        embedding_client=embedding_client,
                        structure_client=structure_client,
                        post_title=title,
                    )
            imported += 1
        cleanup = await cleanup_synthetic_seed(target, apply=True)
        # A fresh corpus has no activated estimate yet (chicken-and-egg:
        # estimation samples the imported corpus), and product
        # reconstruction never falls back to hand-picked constants
        # (ADR 0200 point 1). Skip the rebuild with a next-action note
        # instead of failing the whole import.
        try:
            edges = await rebuild_lineage(target, llm=adjudication_client)
            lineage_summary: dict[str, object] = {"lineage_edges": len(edges)}
        except ChannelWeightsNotEstimated as exc:
            lineage_summary = {
                "lineage_edges": None,
                "lineage_rebuild_skipped": (
                    f"{exc} -- after this import, run "
                    "scripts/estimate_channel_weights.py and then "
                    "POST /api/lineage/rebuild"
                ),
            }
        summary: dict[str, object] = {
            "source_rows": len(rows),
            "imported_rows": imported,
            "skipped_rows": skipped,
            **lineage_summary,
            **cleanup,
        }
        if args.no_draft_dimension_evidence.strip():
            summary["no_draft_dimension_evidence"] = (
                args.no_draft_dimension_evidence.strip()
            )
        if args.no_body_dimension_evidence.strip():
            summary["no_body_dimension_evidence"] = (
                args.no_body_dimension_evidence.strip()
            )
        return summary
    finally:
        await source.close()
        await target.close()


def main() -> None:
    """Run the private, caller-mapped import and print aggregate evidence."""
    args = _parser().parse_args()
    print(json.dumps(asyncio.run(import_rows(args)), sort_keys=True))


if __name__ == "__main__":
    main()
