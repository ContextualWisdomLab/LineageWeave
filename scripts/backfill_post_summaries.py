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
from lineageweave.corporate_hierarchy_inference import (
    NullCorporateHierarchyInferenceClient,
)
from lineageweave.embedding_client import orchestrator_embedding_client
from lineageweave.image_content import orchestrator_vision_client
from lineageweave.llm_context import build_post_llm_metadata, use_llm_metadata
from lineageweave.post_content_normalization import normalize_post_body
from lineageweave.post_content_persistence import persist_post_content
from lineageweave.post_structure import (
    ContextualOrchestratorPostStructureClient,
    NullPostStructureClient,
)
from lineageweave.post_summary import ContextualOrchestratorPostSummaryClient
from lineageweave.relation_verification import NullRelationVerificationClient
from lineageweave.semantic_hints import format_semantic_hints


def _post_summary_backfill_parser() -> argparse.ArgumentParser:
    """Build the post-summary backfill command-line parser."""
    argument_parser = argparse.ArgumentParser(description=__doc__)
    argument_parser.add_argument(
        "--target-dsn",
        default=os.environ.get(
            "DATABASE_URL",
            "postgresql://lineageweave:lineageweave_dev_only@localhost:15432/lineageweave",
        ),
    )
    argument_parser.add_argument("--post-id", action="append", dest="post_ids")
    argument_parser.add_argument("--limit", type=int, default=5)
    argument_parser.add_argument(
        "--all",
        action="store_true",
        help="process every eligible post without an explicit project field",
    )
    return argument_parser


def _orchestrator_gateway_config() -> tuple[str, str]:
    """Resolve only the contextual-orchestrator boundary, never its provider."""
    return (
        os.environ.get("ORCHESTRATOR_BASE_URL", ""),
        os.environ.get("ORCHESTRATOR_API_KEY", ""),
    )


def _post_semantic_hints(source_post_record: asyncpg.Record) -> str:
    """Format semantic hints from one selected source-post record."""
    source_author_name = source_post_record["source_author_name"]
    if (
        source_author_name
        and source_author_name == source_post_record["source_author_code"]
    ):
        source_author_name = None
    return format_semantic_hints(
        author_name=source_author_name or source_post_record["author_name"],
        author_affiliations=source_post_record["author_affiliations"] or (),
        order_pool_code=source_post_record["source_sales_pool_code"],
        order_pool_name=source_post_record["source_sales_pool_name"],
        project_field=source_post_record["project_field"],
        customer_name=source_post_record["customer_name"],
        author_account_id=(
            str(source_post_record["author_account_id"])
            if source_post_record["author_account_id"] is not None
            else None
        ),
        author_account_name=source_post_record["author_name"],
        source_author_code=source_post_record["source_author_code"],
        source_author_name=source_author_name,
        source_company_code=source_post_record["source_company_code"],
        source_company_name=source_post_record["source_company_name"],
        source_company_catalog_name=source_post_record["source_company_catalog_name"],
        source_business_unit_code=source_post_record["source_process_unit_code"],
        source_process_unit_name=source_post_record["source_process_unit_name"],
        source_process_unit_catalog_name=source_post_record[
            "source_process_unit_catalog_name"
        ],
        source_sales_pool_code=source_post_record["source_sales_pool_code"],
        source_sales_pool_name=source_post_record["source_sales_pool_name"],
        source_customer_code=source_post_record["source_customer_code"],
        source_customer_name=source_post_record["source_customer_name"],
        source_customer_catalog_name=source_post_record["source_customer_catalog_name"],
        source_project_code=source_post_record["source_project_code"],
        source_project_name=source_post_record["source_project_name"],
    )


async def _load_summary_source_posts(
    database_connection: asyncpg.Connection,
    requested_post_ids: list[str],
    post_limit: int | None,
) -> list[asyncpg.Record]:
    """Load explicit IDs or one bounded unprojected-post batch."""
    return list(
        await database_connection.fetch(
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
            requested_post_ids or None,
            post_limit,
        )
    )


async def backfill_post_summaries(
    target_dsn: str,
    raw_post_ids: list[str] | None,
    post_limit: int | None,
) -> dict[str, object]:
    """Backfill summaries for explicit posts or one bounded eligible batch."""
    requested_post_ids = [
        str(uuid.UUID(post_id)) for post_id in dict.fromkeys(raw_post_ids or [])
    ]
    orchestrator_base_url, orchestrator_api_key = _orchestrator_gateway_config()
    if not orchestrator_base_url or not orchestrator_api_key:
        raise RuntimeError(
            "contextual-orchestrator gateway credentials are unavailable"
        )

    post_vision_client = orchestrator_vision_client(
        orchestrator_base_url,
        orchestrator_api_key,
    )
    if not post_vision_client.available:
        raise RuntimeError(
            "VISION is unavailable; configure contextual-orchestrator before backfill"
        )
    post_summary_client = ContextualOrchestratorPostSummaryClient(
        orchestrator_base_url,
        orchestrator_api_key,
        timeout=180.0,
    )
    post_embedding_client = orchestrator_embedding_client(
        orchestrator_base_url,
        orchestrator_api_key,
    )
    post_structure_client = (
        ContextualOrchestratorPostStructureClient(
            orchestrator_base_url,
            orchestrator_api_key,
        )
        if orchestrator_base_url and orchestrator_api_key
        else NullPostStructureClient()
    )
    database_connection = await asyncpg.connect(target_dsn)
    try:
        source_post_records = await _load_summary_source_posts(
            database_connection,
            requested_post_ids,
            post_limit,
        )
        backfill_summary: dict[str, object] = {
            "requested_posts": len(requested_post_ids),
            "selected_posts": len(source_post_records),
            "processed_posts": 0,
            "project_mentions": 0,
            "failed_posts": 0,
            "failure_types": {},
        }
        for source_post_record in source_post_records:
            try:
                with use_llm_metadata(
                    build_post_llm_metadata(
                        str(source_post_record["post_id"]),
                        source_post_record,
                    )
                ):
                    normalized_post_content = normalize_post_body(
                        source_post_record["post_body"],
                        vision_client=post_vision_client,
                    )
                    if not normalized_post_content.text.strip():
                        raise ValueError("normalized post body is empty")
                    await persist_post_content(
                        database_connection,
                        str(source_post_record["post_id"]),
                        source_post_record["post_body"],
                        vision_client=post_vision_client,
                        embedding_client=post_embedding_client,
                        normalized_result=normalized_post_content,
                        structure_client=post_structure_client,
                        post_title=source_post_record["post_title"],
                    )
                    post_summary = await asyncio.to_thread(
                        post_summary_client.summarize_with_hints,
                        source_post_record["post_title"],
                        normalized_post_content.text,
                        _post_semantic_hints(source_post_record),
                    )
                    await persist_post_summary(
                        database_connection,
                        str(source_post_record["post_id"]),
                        post_summary,
                        post_body=normalized_post_content.text,
                        hierarchy_inference_client=NullCorporateHierarchyInferenceClient(),
                        verification_client=NullRelationVerificationClient(),
                    )
                backfill_summary["processed_posts"] = (
                    int(backfill_summary["processed_posts"]) + 1
                )
                backfill_summary["project_mentions"] = int(
                    backfill_summary["project_mentions"]
                ) + len(post_summary.project_mentions)
            except Exception as post_failure:  # noqa: BLE001 - continue the batch.
                backfill_summary["failed_posts"] = (
                    int(backfill_summary["failed_posts"]) + 1
                )
                failure_type_counts = backfill_summary["failure_types"]
                assert isinstance(failure_type_counts, dict)
                failure_type_name = type(post_failure).__name__
                failure_type_counts[failure_type_name] = (
                    int(failure_type_counts.get(failure_type_name, 0)) + 1
                )
        return backfill_summary
    finally:
        await database_connection.close()


def main() -> None:
    """Validate command arguments, run the backfill, and print JSON counts."""
    command_arguments = _post_summary_backfill_parser().parse_args()
    if command_arguments.limit < 1:
        raise SystemExit("--limit must be positive")
    if command_arguments.all and command_arguments.post_ids:
        raise SystemExit("--all cannot be combined with --post-id")
    post_limit = (
        None
        if command_arguments.all or command_arguments.post_ids
        else command_arguments.limit
    )
    print(
        json.dumps(
            asyncio.run(
                backfill_post_summaries(
                    command_arguments.target_dsn,
                    command_arguments.post_ids,
                    post_limit,
                )
            ),
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
