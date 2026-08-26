#!/usr/bin/env python3
"""Measure the exact backfill candidate query without exposing source rows."""

from __future__ import annotations

import argparse
import asyncio
import json
import os
from collections import Counter
from collections.abc import Iterator, Mapping
from typing import Any

import asyncpg

from backend.app.post_content_queue import POST_CONTENT_BACKFILL_CANDIDATE_SQL, SUCCEEDED


def _nodes(plan: Mapping[str, Any]) -> Iterator[Mapping[str, Any]]:
    """Yield every PostgreSQL plan node without retaining result rows."""
    yield plan
    for child in plan.get("Plans", ()):
        yield from _nodes(child)


def summarize_plan(document: list[Mapping[str, Any]]) -> dict[str, Any]:
    """Project EXPLAIN JSON into non-identifying aggregate plan evidence."""
    root = document[0]
    nodes = tuple(_nodes(root["Plan"]))
    node_counts = Counter(str(node["Node Type"]) for node in nodes)
    relation_scans = Counter(
        str(node["Relation Name"]) for node in nodes if "Relation Name" in node
    )
    return {
        "planning_time_ms": root.get("Planning Time"),
        "execution_time_ms": root.get("Execution Time"),
        "actual_rows": root["Plan"].get("Actual Rows"),
        "shared_hit_blocks": int(root["Plan"].get("Shared Hit Blocks", 0)),
        "shared_read_blocks": int(root["Plan"].get("Shared Read Blocks", 0)),
        "temp_read_blocks": int(root["Plan"].get("Temp Read Blocks", 0)),
        "temp_written_blocks": int(root["Plan"].get("Temp Written Blocks", 0)),
        "node_counts": dict(sorted(node_counts.items())),
        "relation_scans": dict(sorted(relation_scans.items())),
    }


async def _measure(
    dsn: str,
    *,
    limit: int,
    embeddings: bool,
    structure: bool,
    priority: bool,
) -> dict[str, Any]:
    """Run EXPLAIN inside a rolled-back transaction and return its summary."""
    conn = await asyncpg.connect(dsn)
    transaction = conn.transaction()
    await transaction.start()
    try:
        value = await conn.fetchval(
            "EXPLAIN (ANALYZE, BUFFERS, WAL, FORMAT JSON) "
            + POST_CONTENT_BACKFILL_CANDIDATE_SQL,
            SUCCEEDED,
            embeddings,
            structure,
            limit,
            priority,
        )
        document = json.loads(value) if isinstance(value, str) else value
        return summarize_plan(document)
    finally:
        await transaction.rollback()
        await conn.close()


def main() -> None:
    """Parse bounded operator inputs and print aggregate JSON only."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--dsn", default=os.environ.get("DATABASE_URL"))
    parser.add_argument("--limit", type=int, default=200, choices=range(1, 201))
    parser.add_argument("--embeddings", action="store_true")
    parser.add_argument("--structure", action="store_true")
    parser.add_argument("--tier", choices=("priority", "remaining"), default="priority")
    args = parser.parse_args()
    if not args.dsn:
        parser.error("--dsn or DATABASE_URL is required")
    result = asyncio.run(
        _measure(
            args.dsn,
            limit=args.limit,
            embeddings=args.embeddings,
            structure=args.structure,
            priority=args.tier == "priority",
        )
    )
    result["candidate_tier"] = args.tier
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
