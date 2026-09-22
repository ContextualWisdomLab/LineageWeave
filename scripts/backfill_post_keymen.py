"""Bounded operator backfill for evidence-backed Keyman extraction.

This is intentionally an operator script, not a buyer HTTP route. It reuses
the same contextual-orchestrator boundary and post session metadata as the
per-post extraction endpoint, while keeping the default request count small.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from collections import Counter
from pathlib import Path

import asyncpg

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from backend.app.config import load_settings
from backend.app.keyman_ingestion import ingest_post_keymen
from backend.app.main import (
    _corporate_hierarchy_inference_client,
    _load_post_semantic_hints,
    _organization_name_resolution_client,
    _relation_verification_client,
)
from lineageweave.http_client import HttpClientError
from lineageweave.image_content import orchestrator_vision_client
from lineageweave.keyman_extraction import ContextualOrchestratorKeymanExtractionClient
from lineageweave.llm_context import build_post_llm_metadata, use_llm_metadata
from lineageweave.post_content_normalization import normalize_post_body


def _orchestrator_config() -> tuple[str, str]:
    """Return the published contextual-orchestrator consumer endpoint and bearer."""
    orchestrator_base_url = os.environ.get("ORCHESTRATOR_BASE_URL", "").strip()
    orchestrator_api_key = os.environ.get("ORCHESTRATOR_API_KEY", "").strip()
    if not orchestrator_base_url or not orchestrator_api_key:
        raise RuntimeError(
            "set ORCHESTRATOR_BASE_URL and ORCHESTRATOR_API_KEY to reach "
            "contextual-orchestrator"
        )
    return orchestrator_base_url, orchestrator_api_key


async def _select_posts(
    database_connection: asyncpg.Connection,
    *,
    post_limit: int,
    post_id: str | None,
) -> list[asyncpg.Record]:
    """Select one explicit post or one bounded unprojected batch."""
    if post_id:
        return list(
            await database_connection.fetch(
                """
                select post_id, post_title, post_body, author_account_id,
                       source_author_code, source_company_code,
                       source_customer_code, source_project_code,
                       source_sales_pool_code, source_process_unit_code
                  from source_post post
                 where post.post_id = $1
                   and nullif(btrim(post.source_draft_code), '') is null
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
                """,
                post_id,
            )
        )
    return list(
        await database_connection.fetch(
            """
            select post_id, post_title, post_body, author_account_id,
                   source_author_code, source_company_code,
                   source_customer_code, source_project_code,
                   source_sales_pool_code, source_process_unit_code
              from source_post post
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
               and not exists (
                   select 1
                     from post_person_mention mention
                    where mention.post_id = post.post_id
               )
             order by post.created_at, post.post_id
             limit $1::bigint
            """,
            post_limit,
        )
    )


async def _run_post_keyman_backfill(
    command_arguments: argparse.Namespace,
) -> dict[str, object]:
    """Run the bounded post-Keyman backfill transaction."""
    if command_arguments.post_id and command_arguments.all:
        raise ValueError("--post-id and --all cannot be combined")
    orchestrator_base_url, orchestrator_api_key = _orchestrator_config()
    runtime_settings = load_settings()
    keyman_client = ContextualOrchestratorKeymanExtractionClient(
        base_url=orchestrator_base_url, api_key=orchestrator_api_key, timeout=180.0
    )
    vision_client = orchestrator_vision_client(
        orchestrator_base_url, orchestrator_api_key
    )
    resolution_client = _organization_name_resolution_client()
    verification_client = _relation_verification_client()
    hierarchy_client = _corporate_hierarchy_inference_client()
    post_limit = (
        1
        if command_arguments.post_id or not command_arguments.all
        else command_arguments.limit
    )

    database_pool = await asyncpg.create_pool(
        runtime_settings.database_url, min_size=1, max_size=1
    )
    try:
        async with database_pool.acquire() as database_connection:
            post_records = await _select_posts(
                database_connection,
                post_limit=post_limit,
                post_id=command_arguments.post_id,
            )
            failure_counts: Counter[str] = Counter()
            processed_post_count = 0
            persisted_mention_count = 0
            for post_record in post_records:
                post_id = str(post_record["post_id"])
                try:
                    async with asyncio.timeout(command_arguments.post_timeout):
                        with use_llm_metadata(
                            build_post_llm_metadata(post_id, dict(post_record))
                        ):
                            normalized_post_content = normalize_post_body(
                                post_record["post_body"] or "", vision_client
                            )
                            context_hints = await _load_post_semantic_hints(
                                database_connection, post_id
                            )
                            persisted_mentions = await ingest_post_keymen(
                                database_connection,
                                keyman_client,
                                post_id,
                                post_record["post_title"] or "",
                                normalized_post_content.text,
                                resolution_client=resolution_client,
                                verification_client=verification_client,
                                hierarchy_inference_client=hierarchy_client,
                                context_hints=context_hints,
                            )
                    processed_post_count += 1
                    persisted_mention_count += len(persisted_mentions)
                except TimeoutError:
                    failure_counts["TimeoutError"] += 1
                except (
                    HttpClientError,
                    OSError,
                    RuntimeError,
                    ValueError,
                    asyncpg.PostgresError,
                ) as backfill_error:
                    failure_counts[type(backfill_error).__name__] += 1
        return {
            "failed_posts": sum(failure_counts.values()),
            "failure_types": dict(sorted(failure_counts.items())),
            "mentions_persisted": persisted_mention_count,
            "processed_posts": processed_post_count,
            "requested_posts": len(post_records),
        }
    finally:
        await database_pool.close()


def main() -> None:
    """Run the post-Keyman operator and print its JSON summary."""
    argument_parser = argparse.ArgumentParser(description=__doc__)
    post_selector = argument_parser.add_mutually_exclusive_group()
    post_selector.add_argument("--post-id", help="Re-extract one eligible post")
    post_selector.add_argument(
        "--all", action="store_true", help="Process the explicit --limit batch"
    )
    argument_parser.add_argument(
        "--limit", type=int, default=1, help="Maximum posts for --all (default: 1)"
    )
    argument_parser.add_argument(
        "--post-timeout",
        type=float,
        default=240.0,
        help="Maximum seconds per post including provider calls (default: 240)",
    )
    command_arguments = argument_parser.parse_args()
    if command_arguments.limit < 1:
        argument_parser.error("--limit must be positive")
    if command_arguments.post_timeout <= 0:
        argument_parser.error("--post-timeout must be positive")
    print(
        json.dumps(
            asyncio.run(_run_post_keyman_backfill(command_arguments)),
            ensure_ascii=False,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
