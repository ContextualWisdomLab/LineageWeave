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
import uuid
from pathlib import Path
import sys

import asyncpg

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from lineageweave.embedding_client import orchestrator_embedding_client
from lineageweave.image_content import orchestrator_vision_client
from lineageweave.post_content_normalization import normalize_post_body
from lineageweave.post_content_persistence import persist_post_content


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--target-dsn",
        default=os.environ.get("DATABASE_URL", "postgresql://lineageweave:lineageweave_dev_only@localhost:15432/lineageweave"),
    )
    parser.add_argument("--post-id", action="append", required=True, dest="post_ids")
    return parser


async def backfill_post_content(target_dsn: str, raw_post_ids: list[str]) -> dict[str, int]:
    post_ids = [str(uuid.UUID(post_id)) for post_id in dict.fromkeys(raw_post_ids)]
    vision_client = orchestrator_vision_client(
        os.environ.get("ORCHESTRATOR_BASE_URL", ""),
        os.environ.get("ORCHESTRATOR_API_KEY", ""),
        os.environ.get("VISION_MODEL", ""),
    )
    if not vision_client.available:
        raise RuntimeError("VISION is unavailable; configure contextual-orchestrator before backfill")

    embedding_model = os.environ.get("LLM_GATEWAY_EMBEDDING_MODEL", "").strip()
    embedding_client = orchestrator_embedding_client(
        os.environ.get("ORCHESTRATOR_BASE_URL", ""),
        os.environ.get("ORCHESTRATOR_API_KEY", ""),
        embedding_model,
    )
    conn = await asyncpg.connect(target_dsn)
    try:
        rows = await conn.fetch(
            "select post_id, post_body from source_post where post_id = any($1::uuid[])",
            post_ids,
        )
        if len(rows) != len(post_ids):
            raise ValueError("one or more requested post IDs were not found")

        result = {
            "requested_posts": len(post_ids),
            "described_posts": 0,
            "described_images": 0,
            "described_regions": 0,
            "embedding_rows": 0,
            "skipped_posts": 0,
        }
        for row in rows:
            normalized = normalize_post_body(row["post_body"], vision_client=vision_client)
            described_images = sum(item.status_code == "described" for item in normalized.image_results)
            if described_images == 0:
                result["skipped_posts"] += 1
                continue
            await persist_post_content(
                conn,
                str(row["post_id"]),
                row["post_body"],
                vision_client=vision_client,
                embedding_client=embedding_client,
                embedding_model_code=embedding_model or None,
                normalized_result=normalized,
            )
            result["described_posts"] += 1
            result["described_images"] += described_images
            result["described_regions"] += sum(
                len(item.regions) for item in normalized.image_results if item.status_code == "described"
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
    print(json.dumps(asyncio.run(backfill_post_content(args.target_dsn, args.post_ids)), sort_keys=True))


if __name__ == "__main__":
    main()
