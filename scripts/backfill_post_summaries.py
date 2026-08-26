#!/usr/bin/env python3
"""Backfill evidence-backed summaries for posts without a project field.

This is an operator command, not a buyer HTTP route. It uses the existing
post-summary contract through contextual-orchestrator, keeps one metadata
session per post, and never prints source bodies or model responses.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
import uuid
from pathlib import Path

import asyncpg

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from backend.app.post_summary_ingestion import persist_post_summary
from lineageweave.corporate_hierarchy_inference import NullCorporateHierarchyInferenceClient
from lineageweave.embedding_client import orchestrator_embedding_client
from lineageweave.image_content import orchestrator_vision_client
from lineageweave.llm_context import build_post_llm_metadata, use_llm_metadata
from lineageweave.post_content_normalization import normalize_post_body
from lineageweave.post_content_persistence import persist_post_content
from lineageweave.post_structure import ContextualOrchestratorPostStructureClient, NullPostStructureClient
from lineageweave.post_summary import ContextualOrchestratorPostSummaryClient
from lineageweave.relation_verification import NullRelationVerificationClient
from lineageweave.semantic_hints import format_semantic_hints


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--target-dsn",
        default=os.environ.get(
            "DATABASE_URL",
            "postgresql://lineageweave:lineageweave_dev_only@localhost:15432/lineageweave",
        ),
    )
    parser.add_argument("--post-id", action="append", dest="post_ids")
    parser.add_argument("--limit", type=int, default=5)
    parser.add_argument(
        "--all",
        action="store_true",
        help="process every eligible post without an explicit project field",
    )
    return parser


def _gateway_config() -> tuple[str, str]:
    """Resolve only the contextual-orchestrator boundary, never its provider."""
    return (
        os.environ.get("ORCHESTRATOR_BASE_URL", ""),
        os.environ.get("ORCHESTRATOR_API_KEY", ""),
    )


def _semantic_hints(row: asyncpg.Record) -> str:
    source_author_name = row["source_author_name"]
    if source_author_name and source_author_name == row["source_author_code"]:
        source_author_name = None
    return format_semantic_hints(
        author_name=source_author_name or row["author_name"],
        author_affiliations=row["author_affiliations"] or (),
        order_pool_code=row["source_sales_pool_code"],
        order_pool_name=row["source_sales_pool_name"],
        project_field=row["project_field"],
        customer_name=row["customer_name"],
        author_account_id=(
            str(row["author_account_id"]) if row["author_account_id"] is not None else None
        ),
        author_account_name=row["author_name"],
        source_author_code=row["source_author_code"],
        source_author_name=source_author_name,
        source_company_code=row["source_company_code"],
        source_company_name=row["source_company_name"],
        source_company_catalog_name=row["source_company_catalog_name"],
        source_business_unit_code=row["source_process_unit_code"],
        source_process_unit_name=row["source_process_unit_name"],
        source_process_unit_catalog_name=row["source_process_unit_catalog_name"],
        source_sales_pool_code=row["source_sales_pool_code"],
        source_sales_pool_name=row["source_sales_pool_name"],
        source_customer_code=row["source_customer_code"],
        source_customer_name=row["source_customer_name"],
        source_customer_catalog_name=row["source_customer_catalog_name"],
        source_project_code=row["source_project_code"],
        source_project_name=row["source_project_name"],
        source_voc_type_code=row["voc_type_code"],
        source_stage_code=row["source_stage_code"],
        source_detail_state_code=row["source_detail_state_code"],
    )


async def _load_posts(
    conn: asyncpg.Connection,
    post_ids: list[str],
    limit: int | None,
) -> list[asyncpg.Record]:
    """Load explicit IDs or one bounded unprojected-post batch."""
    return list(
        await conn.fetch(
            """
            select post.post_id,
                   post.post_title,
                   post.post_body,
                   post.author_account_id,
                   author.display_name as author_name,
                   post.source_author_code,
                   post.source_author_name,
                   post.source_company_code,
                   post.source_company_name,
                   source_company.entity_name as source_company_catalog_name,
                   post.source_process_unit_code,
                   post.source_process_unit_name,
                   source_process_unit.process_unit_name as source_process_unit_catalog_name,
                   post.source_sales_pool_code,
                   post.source_sales_pool_name,
                   post.source_customer_code,
                   post.source_customer_name,
                   source_customer.entity_name as source_customer_catalog_name,
                   post.source_project_code,
                   post.source_project_name,
                   post.voc_type_code,
                   post.source_stage_code,
                   post.source_detail_state_code,
                   post.secondary_grouping_key as project_field,
                   customer.entity_name as customer_name,
                   coalesce(
                       (
                           select array_agg(distinct affiliated.entity_name)
                             from account_affiliation affiliation
                             join corporate_entity affiliated
                               on affiliated.corporate_entity_id = affiliation.corporate_entity_id
                            where affiliation.user_account_id = post.author_account_id
                       ),
                       '{}'::text[]
                   ) as author_affiliations
              from source_post post
              left join user_account author
                on author.user_account_id = post.author_account_id
              left join corporate_entity customer
                on customer.corporate_entity_id = post.corporate_entity_id
              left join corporate_entity source_company
                on source_company.corporate_entity_code = nullif(btrim(post.source_company_code), '')
              left join process_unit source_process_unit
                on source_process_unit.process_unit_code = nullif(btrim(post.source_process_unit_code), '')
              left join corporate_entity source_customer
                on source_customer.corporate_entity_code = nullif(btrim(post.source_customer_code), '')
             where nullif(btrim(post.source_draft_code), '') is null
               and nullif(btrim(post.source_deleted_flag), '') is null
               and not (
                   (
                       nullif(btrim(post.source_author_code), '') is null
                       and nullif(btrim(post.source_author_name), '') is null
                       and nullif(btrim(post.source_company_code), '') is null
                       and nullif(btrim(post.source_company_name), '') is null
                       and nullif(btrim(post.source_process_unit_code), '') is null
                       and nullif(btrim(post.source_process_unit_name), '') is null
                       and nullif(btrim(post.source_sales_pool_code), '') is null
                       and nullif(btrim(post.source_sales_pool_name), '') is null
                       and nullif(btrim(post.source_customer_code), '') is null
                       and nullif(btrim(post.source_customer_name), '') is null
                       and nullif(btrim(post.source_project_code), '') is null
                       and nullif(btrim(post.source_project_name), '') is null
                   )
                   and exists (
                       select 1
                         from source_post real_post
                        where (
                            nullif(btrim(real_post.source_author_code), '') is not null
                            or nullif(btrim(real_post.source_author_name), '') is not null
                            or nullif(btrim(real_post.source_company_code), '') is not null
                            or nullif(btrim(real_post.source_company_name), '') is not null
                            or nullif(btrim(real_post.source_process_unit_code), '') is not null
                            or nullif(btrim(real_post.source_process_unit_name), '') is not null
                            or nullif(btrim(real_post.source_sales_pool_code), '') is not null
                            or nullif(btrim(real_post.source_sales_pool_name), '') is not null
                            or nullif(btrim(real_post.source_customer_code), '') is not null
                            or nullif(btrim(real_post.source_customer_name), '') is not null
                            or nullif(btrim(real_post.source_project_code), '') is not null
                            or nullif(btrim(real_post.source_project_name), '') is not null
                        )
                   )
               )
               and (
                   (
                       $1::uuid[] is not null
                       and post.post_id = any($1::uuid[])
                   )
                   or (
                       $1::uuid[] is null
                       and nullif(btrim(post.source_project_code::text), '') is null
                       and nullif(btrim(post.source_project_name::text), '') is null
                       and not exists (
                           select 1
                             from post_project_mention mention
                            where mention.post_id = post.post_id
                       )
                   )
               )
             order by post.created_at, post.post_id
             limit $2::bigint
            """,
            post_ids or None,
            limit,
        )
    )


async def backfill_post_summaries(
    target_dsn: str,
    raw_post_ids: list[str] | None,
    limit: int | None,
) -> dict[str, object]:
    post_ids = [str(uuid.UUID(post_id)) for post_id in dict.fromkeys(raw_post_ids or [])]
    base_url, api_key = _gateway_config()
    if not base_url or not api_key:
        raise RuntimeError("contextual-orchestrator gateway credentials are unavailable")

    vision_client = orchestrator_vision_client(base_url, api_key)
    if not vision_client.available:
        raise RuntimeError("VISION is unavailable; configure contextual-orchestrator before backfill")
    summary_client = ContextualOrchestratorPostSummaryClient(base_url, api_key, timeout=180.0)
    embedding_client = orchestrator_embedding_client(base_url, api_key)
    structure_client = (
        ContextualOrchestratorPostStructureClient(base_url, api_key)
        if base_url and api_key
        else NullPostStructureClient()
    )
    conn = await asyncpg.connect(target_dsn)
    try:
        rows = await _load_posts(conn, post_ids, limit)
        result: dict[str, object] = {
            "requested_posts": len(post_ids),
            "selected_posts": len(rows),
            "processed_posts": 0,
            "project_mentions": 0,
            "failed_posts": 0,
            "failure_types": {},
        }
        for row in rows:
            try:
                with use_llm_metadata(build_post_llm_metadata(str(row["post_id"]), row)):
                    normalized = normalize_post_body(row["post_body"], vision_client=vision_client)
                    if not normalized.text.strip():
                        raise ValueError("normalized post body is empty")
                    await persist_post_content(
                        conn,
                        str(row["post_id"]),
                        row["post_body"],
                        vision_client=vision_client,
                        embedding_client=embedding_client,
                        normalized_result=normalized,
                        structure_client=structure_client,
                        post_title=row["post_title"],
                    )
                    summary = await asyncio.to_thread(
                        summary_client.summarize_with_hints,
                        row["post_title"],
                        normalized.text,
                        _semantic_hints(row),
                    )
                    await persist_post_summary(
                        conn,
                        str(row["post_id"]),
                        summary,
                        post_body=normalized.text,
                        hierarchy_inference_client=NullCorporateHierarchyInferenceClient(),
                        verification_client=NullRelationVerificationClient(),
                    )
                result["processed_posts"] = int(result["processed_posts"]) + 1
                result["project_mentions"] = int(result["project_mentions"]) + len(summary.project_mentions)
            except Exception as exc:  # noqa: BLE001 - one post must not hide other progress.
                result["failed_posts"] = int(result["failed_posts"]) + 1
                failures = result["failure_types"]
                assert isinstance(failures, dict)
                name = type(exc).__name__
                failures[name] = int(failures.get(name, 0)) + 1
        return result
    finally:
        await conn.close()


def main() -> None:
    args = _parser().parse_args()
    if args.limit < 1:
        raise SystemExit("--limit must be positive")
    if args.all and args.post_ids:
        raise SystemExit("--all cannot be combined with --post-id")
    limit = None if args.all or args.post_ids else args.limit
    print(
        json.dumps(
            asyncio.run(backfill_post_summaries(args.target_dsn, args.post_ids, limit)),
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
