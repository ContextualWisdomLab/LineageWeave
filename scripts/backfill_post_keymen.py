"""Bounded operator backfill for evidence-backed Keyman extraction.

This is intentionally an operator script, not a buyer HTTP route. It reuses
the same contextual-orchestrator boundary and post session metadata as the
per-post extraction endpoint, while keeping the default request count small.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import math
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
    base_url = os.environ.get("ORCHESTRATOR_BASE_URL", "").strip()
    api_key = os.environ.get("ORCHESTRATOR_API_KEY", "").strip()
    if not base_url or not api_key:
        raise RuntimeError(
            "set ORCHESTRATOR_BASE_URL and ORCHESTRATOR_API_KEY to reach "
            "contextual-orchestrator"
        )
    return base_url, api_key


def _post_timeout_is_valid(post_timeout: object) -> bool:
    """Return whether an operator timeout is a finite, strictly positive number."""
    return (
        type(post_timeout) in (int, float)
        and math.isfinite(post_timeout)
        and post_timeout > 0
    )


def _post_limit_is_valid(post_limit: object) -> bool:
    """Return whether a batch limit is an exact, strictly positive integer."""
    return type(post_limit) is int and post_limit > 0


def _post_id_is_valid(post_id: object) -> bool:
    """Return whether an optional explicit post identity is exact canonical text."""
    return (
        post_id is None
        or type(post_id) is str
        and bool(post_id)
        and post_id == post_id.strip()
    )


async def _select_posts(
    conn: asyncpg.Connection, *, limit: int, post_id: str | None
) -> list[asyncpg.Record]:
    """Select one explicit post or one bounded unprojected batch."""
    if post_id:
        return list(
            await conn.fetch(
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
        await conn.fetch(
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
            limit,
        )
    )


async def _run_post_keymen_backfill(
    backfill_arguments: argparse.Namespace,
) -> dict[str, object]:
    """Execute one bounded post-Keyman backfill operation."""
    if not _post_timeout_is_valid(backfill_arguments.post_timeout):
        raise ValueError("--post-timeout must be finite and positive")
    if not _post_limit_is_valid(backfill_arguments.limit):
        raise ValueError("--limit must be a positive integer")
    if not _post_id_is_valid(backfill_arguments.post_id):
        raise ValueError("--post-id must be nonblank and unpadded")
    if backfill_arguments.post_id and backfill_arguments.all:
        raise ValueError("--post-id and --all cannot be combined")
    base_url, api_key = _orchestrator_config()
    settings = load_settings()
    keyman_client = ContextualOrchestratorKeymanExtractionClient(
        base_url=base_url, api_key=api_key, timeout=180.0
    )
    vision_client = orchestrator_vision_client(base_url, api_key)
    resolution_client = _organization_name_resolution_client()
    verification_client = _relation_verification_client()
    hierarchy_client = _corporate_hierarchy_inference_client()
    limit = (
        1
        if backfill_arguments.post_id or not backfill_arguments.all
        else backfill_arguments.limit
    )

    pool = await asyncpg.create_pool(settings.database_url, min_size=1, max_size=1)
    try:
        async with pool.acquire() as conn:
            rows = await _select_posts(
                conn, limit=limit, post_id=backfill_arguments.post_id
            )
            failures: Counter[str] = Counter()
            processed = 0
            mention_count = 0
            for row in rows:
                post_id = str(row["post_id"])
                try:
                    async with asyncio.timeout(backfill_arguments.post_timeout):
                        with use_llm_metadata(build_post_llm_metadata(post_id, dict(row))):
                            normalized = normalize_post_body(row["post_body"] or "", vision_client)
                            context_hints = await _load_post_semantic_hints(conn, post_id)
                            mentions = await ingest_post_keymen(
                                conn,
                                keyman_client,
                                post_id,
                                row["post_title"] or "",
                                normalized.text,
                                resolution_client=resolution_client,
                                verification_client=verification_client,
                                hierarchy_inference_client=hierarchy_client,
                                context_hints=context_hints,
                            )
                    processed += 1
                    mention_count += len(mentions)
                except TimeoutError:
                    failures["TimeoutError"] += 1
                except (HttpClientError, OSError, RuntimeError, ValueError, asyncpg.PostgresError) as exc:
                    failures[type(exc).__name__] += 1
        return {
            "failed_posts": sum(failures.values()),
            "failure_types": dict(sorted(failures.items())),
            "mentions_persisted": mention_count,
            "processed_posts": processed,
            "requested_posts": len(rows),
        }
    finally:
        await pool.close()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    selector = parser.add_mutually_exclusive_group()
    selector.add_argument("--post-id", help="Re-extract one eligible post")
    selector.add_argument("--all", action="store_true", help="Process the explicit --limit batch")
    parser.add_argument("--limit", type=int, default=1, help="Maximum posts for --all (default: 1)")
    parser.add_argument(
        "--post-timeout",
        type=float,
        default=240.0,
        help="Maximum seconds per post including provider calls (default: 240)",
    )
    backfill_arguments = parser.parse_args()
    if not _post_limit_is_valid(backfill_arguments.limit):
        parser.error("--limit must be a positive integer")
    if not _post_timeout_is_valid(backfill_arguments.post_timeout):
        parser.error("--post-timeout must be finite and positive")
    if not _post_id_is_valid(backfill_arguments.post_id):
        parser.error("--post-id must be nonblank and unpadded")
    print(
        json.dumps(
            asyncio.run(_run_post_keymen_backfill(backfill_arguments)),
            ensure_ascii=False,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
