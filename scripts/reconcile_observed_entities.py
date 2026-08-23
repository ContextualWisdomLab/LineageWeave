"""Nightly full-corpus backstop for ``account_observed_entity`` (ADR 0144).

The synchronous path (``record_observed_entity`` at ingestion time,
``prune_observed_entity_for_posts`` inline with the one production
``source_post.corporate_entity_id`` reassignment) keeps
``account_observed_entity`` correct for events it actually sees. This
script is the backstop for events it cannot see: an ``account_affiliation``
grant added after a post's entities were already observed (a real account
should widen access but nothing re-runs the write-time hook for it), or
any other drift the synchronous path missed. Same operator-script shape as
``backfill_customer_hints.py`` -- bounded batch, JSON summary, no reader-
facing HTTP route.

For each already-recorded ``(corporate_entity_id, source_post_id)`` pair,
replays the same two operations the synchronous path performs: re-run the
write-time hook (picks up newly-eligible accounts; a no-op for accounts
already recorded) and re-run the prune (drops accounts that lost
eligibility since the last observation). Never invents a new observation
this repo's own ABAC predicate would not already grant.
"""

from __future__ import annotations

import argparse
import asyncio
import json

import asyncpg

from backend.app.config import load_settings
from backend.app.corporate_entity_ingestion import (
    prune_observed_entity_for_posts,
    record_observed_entity,
)


async def _select_pairs(
    conn: asyncpg.Connection, *, limit: int
) -> list[asyncpg.Record]:
    """A bounded batch of distinct (corporate_entity_id, source_post_id) pairs.

    Oldest ``last_observed_at`` first, so a full-corpus cron sweep visits
    every pair in bounded rounds rather than starving the same tail.
    """
    return await conn.fetch(
        """
        select corporate_entity_id, source_post_id, min(last_observed_at) as last_observed_at
          from account_observed_entity
         group by corporate_entity_id, source_post_id
         order by last_observed_at
         limit $1::bigint
        """,
        limit,
    )


async def _reconcile_batch(
    conn: asyncpg.Connection, pairs: list[asyncpg.Record]
) -> dict[str, object]:
    """Replay the write-time hook and prune for each pair, aggregating errors.

    Isolated from pool/connection setup so the aggregation itself is
    unit-testable without a real database.
    """
    failures: dict[str, int] = {}
    reconciled = 0
    for pair in pairs:
        corporate_entity_id = str(pair["corporate_entity_id"])
        source_post_id = str(pair["source_post_id"])
        try:
            await record_observed_entity(conn, corporate_entity_id, source_post_id)
            await prune_observed_entity_for_posts(conn, [source_post_id])
            reconciled += 1
        except asyncpg.PostgresError as exc:
            failures[type(exc).__name__] = failures.get(type(exc).__name__, 0) + 1
    return {
        "requested_pairs": len(pairs),
        "reconciled_pairs": reconciled,
        "failed_pairs": sum(failures.values()),
        "failure_types": dict(sorted(failures.items())),
    }


async def _run(args: argparse.Namespace) -> dict[str, object]:
    settings = load_settings()
    pool = await asyncpg.create_pool(settings.database_url, min_size=1, max_size=1)
    try:
        async with pool.acquire() as conn:
            pairs = await _select_pairs(conn, limit=args.limit)
            return await _reconcile_batch(conn, pairs)
    finally:
        await pool.close()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--limit",
        type=int,
        default=500,
        help="Maximum (entity, post) pairs to reconcile this run (default: 500)",
    )
    args = parser.parse_args()
    if args.limit < 1:
        parser.error("--limit must be positive")
    print(json.dumps(asyncio.run(_run(args)), ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
