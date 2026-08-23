"""Operator estimation of lineage channel-fusion weights (ADR 0145).

Samples candidate parent-child pairs from the real corpus exactly the
way `reconstruct` forms them (same grouping fallback, same candidate
window), scores each pair on the deterministic channels, fits
`fast-mlsirm`'s multilevel 2PL over the dichotomized scores, and
persists the normalized discriminations into `lineage_channel_weight`
(migration 0135). `rebuild_lineage` then uses them automatically on the
next rebuild -- but only when the persisted channel set exactly matches
the rebuild's active channels, so a partial estimate never silently
mixes with hand-picked constants.

This first landing estimates over the three deterministic channels
only; the llm adjudication channel joins the estimate in a follow-up
(each sampled pair then costs a provider call -- ADR 0145 point 5).
Until then the exact-match rule keeps llm-active rebuilds on the
documented fallback. Fails closed: with `fast_mlsirm` not importable or
a degenerate sample, nothing is written and the exit is an explicit
error, never a fabricated weight.
"""

from __future__ import annotations

import argparse
import asyncio
import json

import asyncpg

from backend.app.config import load_settings
from backend.app.lineage_ingestion import records_from_source_posts
from backend.app.post_eligibility import SOURCE_POST_ELIGIBILITY_SQL
from lineageweave.channel_weight_estimation import (
    ChannelWeightEstimate,
    estimate_channel_weights,
)
from lineageweave.channels import (
    secondary_key_match_score,
    temporal_score,
    text_similarity_score,
)
from lineageweave.reconstruct import DEFAULT_CANDIDATE_WINDOW


def sample_pair_scores(
    records: list, *, window: int = DEFAULT_CANDIDATE_WINDOW
) -> tuple[list[dict[str, float]], list[int]]:
    """Score every in-window candidate pair, grouped as reconstruct groups.

    Pure so the sampling geometry itself is unit-testable: pairs come
    only from within one group, only from the trailing ``window`` of
    temporally prior records -- the exact candidate set
    ``reconstruct._reconstruct_group`` would consider.
    """
    groups: dict[str, list] = {}
    for record in records:
        groups.setdefault(record.group_key, []).append(record)

    pair_scores: list[dict[str, float]] = []
    group_ids: list[int] = []
    for group_index, group_records in enumerate(groups.values()):
        ordered = sorted(group_records, key=lambda r: r.occurred_at)
        for index, record in enumerate(ordered):
            for candidate in ordered[max(0, index - window) : index]:
                pair_scores.append(
                    {
                        "temporal": temporal_score(candidate, record),
                        "secondary_key": secondary_key_match_score(candidate, record),
                        "text": text_similarity_score(candidate, record),
                    }
                )
                group_ids.append(group_index)
    return pair_scores, group_ids


async def persist_estimate(
    conn: asyncpg.Connection, estimate: ChannelWeightEstimate
) -> None:
    """Replace the persisted weight set atomically with this estimate."""
    async with conn.transaction():
        await conn.execute("delete from lineage_channel_weight")
        for channel, weight in estimate.weights.items():
            await conn.execute(
                """
                insert into lineage_channel_weight
                    (channel_code, weight_value, estimation_method_code, sample_pair_count)
                values ($1, $2, $3, $4)
                """,
                channel,
                weight,
                estimate.estimation_method_code,
                estimate.sample_pair_count,
            )


async def _run(args: argparse.Namespace) -> dict[str, object]:
    settings = load_settings()
    pool = await asyncpg.create_pool(settings.database_url, min_size=1, max_size=1)
    try:
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                "select post_id, post_title, voc_type_code, created_at, "
                "corporate_entity_id, process_unit_id, thread_group_key, "
                "secondary_grouping_key "
                f"from source_post where {SOURCE_POST_ELIGIBILITY_SQL.format(alias='source_post')} "
                "order by created_at, post_id limit $1::bigint",
                args.post_limit,
            )
            records = records_from_source_posts(rows)
            pair_scores, group_ids = sample_pair_scores(records)
            estimate = estimate_channel_weights(pair_scores, group_ids)
            if estimate is None:
                raise RuntimeError(
                    "no grounded estimate was produced (fast_mlsirm unavailable, "
                    f"sample of {len(pair_scores)} pairs too small, or a channel "
                    "was degenerate) -- nothing was written; rebuilds keep the "
                    "documented fallback weights"
                )
            if not args.dry_run:
                await persist_estimate(conn, estimate)
            return {
                "weights": estimate.weights,
                "sample_pair_count": estimate.sample_pair_count,
                "estimation_method_code": estimate.estimation_method_code,
                "persisted": not args.dry_run,
            }
    finally:
        await pool.close()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--post-limit",
        type=int,
        default=5000,
        help="Maximum eligible posts to sample pairs from (default: 5000)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Estimate and report, but persist nothing",
    )
    args = parser.parse_args()
    if args.post_limit < 1:
        parser.error("--post-limit must be positive")
    print(json.dumps(asyncio.run(_run(args)), ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
