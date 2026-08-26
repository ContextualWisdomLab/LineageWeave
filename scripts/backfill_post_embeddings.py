#!/usr/bin/env python3
"""Bulk-embed existing semantic units without rebuilding or deleting their source rows."""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path

import asyncpg

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from lineageweave.embedding_backfill import backfill_post_content_embeddings
from lineageweave.embedding_client import orchestrator_embedding_client


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--limit", required=True, type=int)
    parser.add_argument(
        "--target-dsn",
        default=os.environ.get(
            "DATABASE_URL",
            "postgresql://lineageweave:lineageweave_dev_only@localhost:15432/lineageweave",
        ),
    )
    return parser


async def _run(target_dsn: str, input_limit: int) -> dict[str, int | str]:
    client = orchestrator_embedding_client(
        os.environ.get("ORCHESTRATOR_BASE_URL", ""),
        os.environ.get("ORCHESTRATOR_API_KEY", ""),
    )
    if not client.available:
        raise RuntimeError("embedding is unavailable; configure contextual-orchestrator")
    conn = await asyncpg.connect(target_dsn)
    try:
        return await backfill_post_content_embeddings(
            conn, client, input_limit=input_limit
        )
    finally:
        await conn.close()


def main() -> None:
    """Run one operator-bounded embedding batch and print aggregate counts only."""
    args = _parser().parse_args()
    if args.limit < 1:
        raise SystemExit("--limit must be positive")
    print(json.dumps(asyncio.run(_run(args.target_dsn, args.limit)), sort_keys=True))


if __name__ == "__main__":
    main()
