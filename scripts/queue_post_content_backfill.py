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
    requeue_failed_post_content_jobs,
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
    parser.add_argument(
        "--all-pages",
        action="store_true",
        help="persist every currently eligible page, retaining each job in the durable ledger",
    )
    parser.add_argument(
        "--retry-failed",
        action="store_true",
        help="explicitly reset terminal jobs before queueing incomplete source posts",
    )
    return parser


async def queue_post_content_backfill(
    target_dsn: str,
    valkey_url: str,
    *,
    limit: int,
    all_pages: bool = False,
    retry_failed: bool = False,
) -> dict[str, int]:
    """Queue bounded pages through the shared durable producer and ledger."""
    if not 1 <= limit <= 200:
        raise ValueError("limit must be between 1 and 200")
    settings = load_settings()
    require_orchestrator_evidence = bool(
        settings.orchestrator_base_url and settings.orchestrator_api_key
    )

    pool = await asyncpg.create_pool(target_dsn, min_size=1, max_size=1)
    client = redis.from_url(valkey_url, decode_responses=True)
    try:
        totals = {
            "selected_posts": 0,
            "queued_posts": 0,
            "published_events": 0,
            "recovery_pending": 0,
        }
        producers = []
        if retry_failed:
            producers.append(
                lambda: requeue_failed_post_content_jobs(pool, client, limit=limit)
            )
        producers.append(
            lambda: enqueue_post_content_backfill(
                pool,
                client,
                limit=limit,
                require_embedding=require_orchestrator_evidence,
                require_structure=require_orchestrator_evidence,
            )
        )
        for producer in producers:
            while True:
                page = await producer()
                for key in totals:
                    totals[key] += page[key]
                if not all_pages or page["selected_posts"] < limit:
                    break
        return totals
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
            all_pages=args.all_pages,
            retry_failed=args.retry_failed,
        )
    )
    print(result)


if __name__ == "__main__":
    main()
