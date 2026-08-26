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
    enqueue_post_content_backfill,
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
    parser.add_argument("--limit", type=int, choices=range(1, 201), default=100)
    return parser


async def queue_post_content_backfill(
    target_dsn: str,
    valkey_url: str,
    *,
    limit: int,
) -> dict[str, int | bool]:
    """Queue one bounded page through the shared durable producer."""
    if not 1 <= limit <= 200:
        raise ValueError("limit must be between 1 and 200")
    settings = load_settings()
    require_orchestrator_evidence = bool(
        settings.orchestrator_base_url and settings.orchestrator_api_key
    )

    pool = await asyncpg.create_pool(target_dsn, min_size=1, max_size=1)
    client = redis.from_url(valkey_url, decode_responses=True)
    try:
        return await enqueue_post_content_backfill(
            pool,
            client,
            limit=limit,
            require_embedding=require_orchestrator_evidence,
            require_structure=require_orchestrator_evidence,
        )
    finally:
        await pool.close()
        await client.aclose()


def main() -> None:
    args = _parser().parse_args()
    result = asyncio.run(
        queue_post_content_backfill(
            args.target_dsn,
            args.valkey_url,
            limit=args.limit,
        )
    )
    print(result)


if __name__ == "__main__":
    main()
