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
from lineageweave.embedding_client import NullEmbeddingClient, orchestrator_embedding_client
from lineageweave.image_content import NullImageContentClient, orchestrator_vision_client
from lineageweave.llm_context import build_post_llm_metadata, use_llm_metadata
from lineageweave.post_content_normalization import normalize_post_body
from lineageweave.post_content_persistence import persist_post_content
from lineageweave.post_structure import ContextualOrchestratorPostStructureClient, NullPostStructureClient


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
        help="process every eligible post without persisted content units",
    )
    parser.add_argument(
        "--normalize-only",
        action="store_true",
        help="persist deterministic DOM/text units without VISION, structure, or embedding calls",
    )
    return parser


async def backfill_post_content(
    target_dsn: str,
    raw_post_ids: list[str] | None,
    limit: int | None,
    normalize_only: bool = False,
) -> dict[str, int]:
    post_ids = [str(uuid.UUID(post_id)) for post_id in dict.fromkeys(raw_post_ids or [])]
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
            raise RuntimeError("VISION is unavailable; configure contextual-orchestrator before backfill")

        embedding_client = orchestrator_embedding_client(
            orchestrator_base_url,
            orchestrator_api_key,
        )
        if not embedding_client.available:
            raise RuntimeError(
                "embedding is unavailable; configure contextual-orchestrator before backfill"
            )
        structure_client = (
            ContextualOrchestratorPostStructureClient(orchestrator_base_url, orchestrator_api_key)
            if orchestrator_base_url and orchestrator_api_key
            else NullPostStructureClient()
        )
    conn = await asyncpg.connect(target_dsn)
    try:
        selected_rows = await conn.fetch(
            """
            select post.post_id
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
               and (
                   (
                       $1::uuid[] is not null
                       and post.post_id = any($1::uuid[])
                   )
                   or (
                       $1::uuid[] is null
                       and (
                           (
                               $2::boolean
                               and not exists (
                                   select 1
                                     from post_content_unit unit
                                    where unit.post_id = post.post_id
                               )
                           )
                           or (
                               not $2::boolean
                               and (
                                   not exists (
                                       select 1
                                         from post_content_unit unit
                                        where unit.post_id = post.post_id
                                   )
                                   or exists (
                                       select 1
                                         from post_content_unit unit
                                         left join post_content_embedding embedding
                                           on embedding.post_content_unit_id = unit.post_content_unit_id
                                        where unit.post_id = post.post_id
                                          and embedding.post_content_unit_id is null
                                   )
                               )
                           )
                       )
                   )
               )
             order by post.created_at, post.post_id
             limit $3::bigint
            """,
            post_ids or None,
            normalize_only,
            limit,
        )
        if post_ids and len(selected_rows) != len(post_ids):
            raise ValueError("one or more requested post IDs were not found")

        result = {
            "requested_posts": len(post_ids),
            "selected_posts": len(selected_rows),
            "processed_posts": 0,
            "described_posts": 0,
            "described_images": 0,
            "described_regions": 0,
            "embedding_rows": 0,
            "skipped_posts": 0,
        }
        for selected_row in selected_rows:
            row = await conn.fetchrow(
                """
                select post.post_id, post.post_title, post.post_body, post.author_account_id,
                       post.source_process_unit_code, post.source_author_code,
                       post.source_company_code, post.source_customer_code,
                       post.source_project_code, post.source_sales_pool_code,
                       entity.corporate_entity_code
                  from source_post post
                  left join corporate_entity entity
                    on entity.corporate_entity_id = post.corporate_entity_id
                 where post.post_id = $1
                """,
                selected_row["post_id"],
            )
            if row is None:
                continue
            with use_llm_metadata(build_post_llm_metadata(str(row["post_id"]), row)):
                normalized = normalize_post_body(row["post_body"], vision_client=vision_client)
                described_images = sum(
                    item.status_code == "described" for item in normalized.image_results
                )
                if described_images == 0 and not normalized.text.strip():
                    result["skipped_posts"] += 1
                    continue
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
                async with conn.transaction():
                    await record_post_content_backfill_success(
                        conn,
                        str(row["post_id"]),
                        str(row["post_body"] or ""),
                    )
            result["processed_posts"] += 1
            if described_images:
                result["described_posts"] += 1
            result["described_images"] += described_images
            result["described_regions"] += sum(
                len(item.regions)
                for item in normalized.image_results
                if item.status_code == "described"
            )
            result["embedding_rows"] += await conn.fetchval(
                """
                select count(*)
                  from post_content_embedding embedding
                  join post_content_unit unit using (post_content_unit_id)
                 where unit.post_id = $1
                """,
                row["post_id"],
            )
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
            asyncio.run(
                backfill_post_content(
                    args.target_dsn,
                    args.post_ids,
                    limit,
                    args.normalize_only,
                )
            ),
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
