#!/usr/bin/env python3
"""Queue incomplete real post-content jobs through PostgreSQL and Valkey."""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
from pathlib import Path

import asyncpg
import redis.asyncio as redis

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from backend.app.post_content_queue import (  # noqa: E402
    ensure_post_content_job,
    post_content_is_complete,
    publish_post_content_event,
)
from backend.app.config import load_settings  # noqa: E402


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--target-dsn",
        default=os.environ.get(
            "DATABASE_URL",
            "postgresql://lineageweave:lineageweave_dev_only@localhost:15432/lineageweave",
        ),
    )
    parser.add_argument(
        "--valkey-url",
        default=os.environ.get("VALKEY_URL", "redis://localhost:16379/0"),
    )
    parser.add_argument("--limit", type=int, default=100)
    parser.add_argument("--all", action="store_true", help="scan the complete real corpus")
    return parser


async def queue_post_content_backfill(
    target_dsn: str,
    valkey_url: str,
    *,
    limit: int | None,
) -> dict[str, int]:
    if limit is not None and limit < 1:
        raise ValueError("limit must be positive")
    settings = load_settings()
    require_orchestrator_evidence = bool(
        settings.orchestrator_base_url and settings.orchestrator_api_key
    )

    connection = await asyncpg.connect(target_dsn)
    client = redis.from_url(valkey_url, decode_responses=True)
    result = {"scanned_posts": 0, "already_complete": 0, "queued_posts": 0, "published_events": 0}
    try:
        rows = await connection.fetch(
            """
            select post_id, post_body
              from source_post post
             where nullif(btrim(source_draft_code), '') is null
               and nullif(btrim(source_deleted_flag), '') is null
               and (
                   nullif(btrim(source_author_code), '') is not null
                   or nullif(btrim(source_author_name), '') is not null
                   or nullif(btrim(source_company_code), '') is not null
                   or nullif(btrim(source_company_name), '') is not null
                   or nullif(btrim(source_process_unit_code), '') is not null
                   or nullif(btrim(source_process_unit_name), '') is not null
                   or nullif(btrim(source_sales_pool_code), '') is not null
                   or nullif(btrim(source_sales_pool_name), '') is not null
                   or nullif(btrim(source_customer_code), '') is not null
                   or nullif(btrim(source_customer_name), '') is not null
                   or nullif(btrim(source_project_code), '') is not null
                   or nullif(btrim(source_project_name), '') is not null
               )
               and (
                   not exists (
                       select 1
                         from post_content_unit unit
                        where unit.post_id = post.post_id
                   )
                   or ($1::boolean and exists (
                       select 1
                         from post_content_unit unit
                         left join post_content_embedding embedding
                           on embedding.post_content_unit_id = unit.post_content_unit_id
                        where unit.post_id = post.post_id
                          and embedding.post_content_embedding_id is null
                   ))
                   or ($1::boolean and exists (
                       select 1
                         from post_content_unit unit
                         join post_content_image image
                           on image.post_content_unit_id = unit.post_content_unit_id
                         join post_content_image_region region
                           on region.post_content_image_id = image.post_content_image_id
                         left join post_content_image_region_embedding embedding
                           on embedding.post_content_image_region_id = region.post_content_image_region_id
                        where unit.post_id = post.post_id
                          and region.description_status_code = 'described'
                           and embedding.post_content_image_region_embedding_id is null
                   ))
                   or ($2::boolean and exists (
                       select 1
                         from post_content_unit unit
                         left join post_content_unit_structure structure
                           on structure.post_content_unit_id = unit.post_content_unit_id
                        where unit.post_id = post.post_id
                          and unit.unit_kind_code <> 'image'
                          and (
                              structure.post_content_unit_structure_id is null
                              or structure.decision_source_code = 'unresolved'
                          )
                   ))
               )
             order by post.created_at, post.post_id
             limit $3::bigint
            """,
            require_orchestrator_evidence,
            require_orchestrator_evidence,
            limit if limit is not None else 9223372036854775807,
        )
        for row in rows:
            result["scanned_posts"] += 1
            post_id = str(row["post_id"])
            async with connection.transaction():
                complete = await post_content_is_complete(
                    connection,
                    post_id,
                    require_embedding=require_orchestrator_evidence,
                    require_structure=require_orchestrator_evidence,
                )
                request = await ensure_post_content_job(
                    connection,
                    post_id,
                    str(row["post_body"] or ""),
                    content_complete=complete,
                )
            if complete and not request.should_publish:
                result["already_complete"] += 1
                continue
            if request.should_publish:
                entry_id = await publish_post_content_event(
                    client,
                    post_id=post_id,
                    source_body_digest=request.source_body_sha256,
                )
                if entry_id is None:
                    raise RuntimeError(f"Valkey did not publish post-content job {post_id}")
                result["published_events"] += 1
                result["queued_posts"] += 1
        return result
    finally:
        await connection.close()
        await client.aclose()


def main() -> None:
    args = _parser().parse_args()
    result = asyncio.run(
        queue_post_content_backfill(
            args.target_dsn,
            args.valkey_url,
            limit=None if args.all else args.limit,
        )
    )
    print(result)


if __name__ == "__main__":
    main()
