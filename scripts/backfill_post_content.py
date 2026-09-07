#!/usr/bin/env python3
"""Reprocess selected stored posts through the existing content pipeline.

This is an operator command, not a buyer HTTP route. It is intentionally
post-id scoped so a VISION failure cannot trigger an unbounded spend or rewrite
the whole corpus. Raw post bodies and model responses are never printed.
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

from backend.app.post_content_queue import record_post_content_backfill_success
from lineageweave.embedding_client import (
    NullEmbeddingClient,
    orchestrator_embedding_client,
)
from lineageweave.image_content import (
    NullImageContentClient,
    orchestrator_vision_client,
)
from lineageweave.llm_context import build_post_llm_metadata, use_llm_metadata
from lineageweave.post_content_normalization import normalize_post_body
from lineageweave.post_content_persistence import persist_post_content
from lineageweave.post_structure import (
    ContextualOrchestratorPostStructureClient,
    NullPostStructureClient,
)


def _post_content_backfill_parser() -> argparse.ArgumentParser:
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
        help="process every eligible post without persisted content units",
    )
    argument_parser.add_argument(
        "--normalize-only",
        action="store_true",
        help="persist deterministic DOM/text units without VISION, structure, or embedding calls",
    )
    return argument_parser


async def backfill_post_content(
    target_dsn: str,
    raw_post_ids: list[str] | None,
    post_limit: int | None,
    normalize_only: bool = False,
) -> dict[str, int]:
    post_ids = [
        str(uuid.UUID(post_id)) for post_id in dict.fromkeys(raw_post_ids or [])
    ]
    if normalize_only:
        vision_client = NullImageContentClient()
        embedding_client = NullEmbeddingClient()
        structure_client = NullPostStructureClient()
    else:
        orchestrator_base_url = os.environ.get("ORCHESTRATOR_BASE_URL", "")
        orchestrator_api_key = os.environ.get("ORCHESTRATOR_API_KEY", "")
        vision_client = orchestrator_vision_client(
            orchestrator_base_url,
            orchestrator_api_key,
        )
        if not vision_client.available:
            raise RuntimeError(
                "VISION is unavailable; configure contextual-orchestrator before backfill"
            )

        embedding_client = orchestrator_embedding_client(
            orchestrator_base_url,
            orchestrator_api_key,
        )
        if not embedding_client.available:
            raise RuntimeError(
                "embedding is unavailable; configure contextual-orchestrator before backfill"
            )
        structure_client = (
            ContextualOrchestratorPostStructureClient(
                orchestrator_base_url, orchestrator_api_key
            )
            if orchestrator_base_url and orchestrator_api_key
            else NullPostStructureClient()
        )
    database_connection = await asyncpg.connect(target_dsn)
    try:
        selected_post_records = await database_connection.fetch(
            """
            select source_record.post_id
              from source_post source_record
             where nullif(btrim(source_record.source_draft_code), '') is null
               and nullif(btrim(source_record.source_deleted_flag), '') is null
               and not (
                   (
                       nullif(btrim(source_record.source_author_code), '') is null
                       and nullif(btrim(source_record.source_author_name), '') is null
                       and nullif(btrim(source_record.source_company_code), '') is null
                       and nullif(btrim(source_record.source_company_name), '') is null
                       and nullif(btrim(source_record.source_process_unit_code), '') is null
                       and nullif(btrim(source_record.source_process_unit_name), '') is null
                       and nullif(btrim(source_record.source_sales_pool_code), '') is null
                       and nullif(btrim(source_record.source_sales_pool_name), '') is null
                       and nullif(btrim(source_record.source_customer_code), '') is null
                       and nullif(btrim(source_record.source_customer_name), '') is null
                       and nullif(btrim(source_record.source_project_code), '') is null
                       and nullif(btrim(source_record.source_project_name), '') is null
                   )
                   and exists (
                       select 1
                         from source_post attributed_post
                        where (
                            nullif(btrim(attributed_post.source_author_code), '') is not null
                            or nullif(btrim(attributed_post.source_author_name), '') is not null
                            or nullif(btrim(attributed_post.source_company_code), '') is not null
                            or nullif(btrim(attributed_post.source_company_name), '') is not null
                            or nullif(btrim(attributed_post.source_process_unit_code), '') is not null
                            or nullif(btrim(attributed_post.source_process_unit_name), '') is not null
                            or nullif(btrim(attributed_post.source_sales_pool_code), '') is not null
                            or nullif(btrim(attributed_post.source_sales_pool_name), '') is not null
                            or nullif(btrim(attributed_post.source_customer_code), '') is not null
                            or nullif(btrim(attributed_post.source_customer_name), '') is not null
                            or nullif(btrim(attributed_post.source_project_code), '') is not null
                            or nullif(btrim(attributed_post.source_project_name), '') is not null
                        )
                   )
               )
               and (
                   (
                       $1::uuid[] is not null
                       and source_record.post_id = any($1::uuid[])
                   )
                   or (
                       $1::uuid[] is null
                       and (
                           (
                               $2::boolean
                               and not exists (
                                   select 1
                                     from post_content_unit content_unit
                                    where content_unit.post_id = source_record.post_id
                               )
                           )
                           or (
                               not $2::boolean
                               and (
                                   not exists (
                                       select 1
                                         from post_content_unit content_unit
                                        where content_unit.post_id = source_record.post_id
                                   )
                                   or exists (
                                       select 1
                                         from post_content_unit content_unit
                                         left join post_content_embedding content_embedding
                                           on content_embedding.post_content_unit_id = content_unit.post_content_unit_id
                                        where content_unit.post_id = source_record.post_id
                                          and content_embedding.post_content_unit_id is null
                                   )
                               )
                           )
                       )
                   )
               )
             order by source_record.created_at, source_record.post_id
             limit $3::bigint
            """,
            post_ids or None,
            normalize_only,
            post_limit,
        )
        if post_ids and len(selected_post_records) != len(post_ids):
            raise ValueError("one or more requested post IDs were not found")

        backfill_summary = {
            "requested_posts": len(post_ids),
            "selected_posts": len(selected_post_records),
            "processed_posts": 0,
            "described_posts": 0,
            "described_images": 0,
            "described_regions": 0,
            "embedding_rows": 0,
            "skipped_posts": 0,
        }
        for selected_post_record in selected_post_records:
            source_post_record = await database_connection.fetchrow(
                """
                select source_record.post_id, source_record.post_title,
                       source_record.post_body, source_record.author_account_id,
                       source_record.source_process_unit_code, source_record.source_author_code,
                       source_record.source_company_code, source_record.source_customer_code,
                       source_record.source_project_code, source_record.source_sales_pool_code,
                       owning_entity.corporate_entity_code
                  from source_post source_record
                  left join corporate_entity owning_entity
                    on owning_entity.corporate_entity_id = source_record.corporate_entity_id
                 where source_record.post_id = $1
                """,
                selected_post_record["post_id"],
            )
            if source_post_record is None:
                continue
            with use_llm_metadata(
                build_post_llm_metadata(
                    str(source_post_record["post_id"]), source_post_record
                )
            ):
                normalized_post_content = normalize_post_body(
                    source_post_record["post_body"], vision_client=vision_client
                )
                described_image_count = sum(
                    image_result.status_code == "described"
                    for image_result in normalized_post_content.image_results
                )
                if (
                    described_image_count == 0
                    and not normalized_post_content.text.strip()
                ):
                    backfill_summary["skipped_posts"] += 1
                    continue
                await persist_post_content(
                    database_connection,
                    str(source_post_record["post_id"]),
                    source_post_record["post_body"],
                    vision_client=vision_client,
                    embedding_client=embedding_client,
                    normalized_result=normalized_post_content,
                    structure_client=structure_client,
                    post_title=source_post_record["post_title"],
                )
                async with database_connection.transaction():
                    await record_post_content_backfill_success(
                        database_connection,
                        str(source_post_record["post_id"]),
                        str(source_post_record["post_body"] or ""),
                    )
            backfill_summary["processed_posts"] += 1
            if described_image_count:
                backfill_summary["described_posts"] += 1
            backfill_summary["described_images"] += described_image_count
            backfill_summary["described_regions"] += sum(
                len(image_result.regions)
                for image_result in normalized_post_content.image_results
                if image_result.status_code == "described"
            )
            backfill_summary["embedding_rows"] += await database_connection.fetchval(
                """
                select count(*)
                  from post_content_embedding content_embedding
                  join post_content_unit content_unit using (post_content_unit_id)
                 where content_unit.post_id = $1
                """,
                source_post_record["post_id"],
            )
        return backfill_summary
    finally:
        await database_connection.close()


def main() -> None:
    command_arguments = _post_content_backfill_parser().parse_args()
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
                backfill_post_content(
                    command_arguments.target_dsn,
                    command_arguments.post_ids,
                    post_limit,
                    command_arguments.normalize_only,
                )
            ),
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
