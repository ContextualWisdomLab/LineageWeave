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


def _queue_backfill_parser() -> argparse.ArgumentParser:
    """Build the post-content queue backfill command parser."""
    argument_parser = argparse.ArgumentParser(description=__doc__)
    argument_parser.add_argument(
        "--target-dsn",
        default=os.environ.get(
            "DATABASE_URL",
            "postgresql://lineageweave:lineageweave_dev_only@localhost:15432/lineageweave",
        ),
    )
    argument_parser.add_argument(
        "--valkey-url",
        default=os.environ.get("VALKEY_URL", "redis://localhost:16379/0"),
    )
    argument_parser.add_argument("--limit", type=int, default=100)
    argument_parser.add_argument(
        "--all", action="store_true", help="scan the complete real corpus"
    )
    return argument_parser


async def queue_post_content_backfill(
    target_dsn: str,
    valkey_url: str,
    *,
    post_limit: int | None,
) -> dict[str, int]:
    """Queue incomplete post-content work and return aggregate counts."""
    if post_limit is not None and post_limit < 1:
        raise ValueError("limit must be positive")
    runtime_settings = load_settings()
    require_orchestrator_evidence = bool(
        runtime_settings.orchestrator_base_url and runtime_settings.orchestrator_api_key
    )

    database_connection = await asyncpg.connect(target_dsn)
    valkey_client = redis.from_url(valkey_url, decode_responses=True)
    backfill_summary = {
        "scanned_posts": 0,
        "already_complete": 0,
        "queued_posts": 0,
        "published_events": 0,
    }
    try:
        source_post_records = await database_connection.fetch(
            """
            select post_id, post_body
              from source_post source_record
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
                         from post_content_unit content_unit
                        where content_unit.post_id = source_record.post_id
                   )
                   or ($1::boolean and exists (
                       select 1
                         from post_content_unit content_unit
                         left join post_content_embedding content_embedding
                           on content_embedding.post_content_unit_id = content_unit.post_content_unit_id
                        where content_unit.post_id = source_record.post_id
                          and content_embedding.post_content_embedding_id is null
                   ))
                   or ($1::boolean and exists (
                       select 1
                         from post_content_unit content_unit
                         join post_content_image content_image
                           on content_image.post_content_unit_id = content_unit.post_content_unit_id
                         join post_content_image_region image_region
                           on image_region.post_content_image_id = content_image.post_content_image_id
                         left join post_content_image_region_embedding region_embedding
                           on region_embedding.post_content_image_region_id = image_region.post_content_image_region_id
                        where content_unit.post_id = source_record.post_id
                          and image_region.description_status_code = 'described'
                           and region_embedding.post_content_image_region_embedding_id is null
                   ))
                   or ($2::boolean and exists (
                       select 1
                         from post_content_unit content_unit
                         left join post_content_unit_structure unit_structure
                           on unit_structure.post_content_unit_id = content_unit.post_content_unit_id
                        where content_unit.post_id = source_record.post_id
                          and content_unit.unit_kind_code <> 'image'
                          and (
                              unit_structure.post_content_unit_structure_id is null
                              or unit_structure.decision_source_code = 'unresolved'
                          )
                   ))
               )
             order by source_record.created_at, source_record.post_id
             limit $3::bigint
            """,
            require_orchestrator_evidence,
            require_orchestrator_evidence,
            post_limit if post_limit is not None else 9223372036854775807,
        )
        for source_post_record in source_post_records:
            backfill_summary["scanned_posts"] += 1
            post_id = str(source_post_record["post_id"])
            async with database_connection.transaction():
                post_content_complete = await post_content_is_complete(
                    database_connection,
                    post_id,
                    require_embedding=require_orchestrator_evidence,
                    require_structure=require_orchestrator_evidence,
                )
                post_content_job_request = await ensure_post_content_job(
                    database_connection,
                    post_id,
                    str(source_post_record["post_body"] or ""),
                    content_complete=post_content_complete,
                )
            if post_content_complete and not post_content_job_request.should_publish:
                backfill_summary["already_complete"] += 1
                continue
            if post_content_job_request.should_publish:
                entry_id = await publish_post_content_event(
                    valkey_client,
                    post_id=post_id,
                    source_body_digest=post_content_job_request.source_body_sha256,
                )
                if entry_id is None:
                    raise RuntimeError(
                        f"Valkey did not publish post-content job {post_id}"
                    )
                backfill_summary["published_events"] += 1
                backfill_summary["queued_posts"] += 1
        return backfill_summary
    finally:
        await database_connection.close()
        await valkey_client.aclose()


def main() -> None:
    """Run the post-content queue backfill command."""
    command_arguments = _queue_backfill_parser().parse_args()
    backfill_summary = asyncio.run(
        queue_post_content_backfill(
            command_arguments.target_dsn,
            command_arguments.valkey_url,
            post_limit=None if command_arguments.all else command_arguments.limit,
        )
    )
    print(backfill_summary)


if __name__ == "__main__":
    main()
