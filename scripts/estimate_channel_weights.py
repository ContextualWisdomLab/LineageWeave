"""Operator estimation of lineage channel-fusion weights (ADR 0145).

Samples candidate parent-child pairs from the real corpus exactly the
way `reconstruct` forms them (same grouping fallback, same candidate
window), scores each pair on the active channels, fits `fast-mlsirm`'s
multilevel 2PL over the dichotomized scores, and persists the
normalized discriminations into `lineage_channel_weight` under the
channel set they were estimated for (migration 0136). Loaders then use
whichever persisted set exactly matches their active channels, so a
partial estimate never silently mixes with hand-picked constants and
the deterministic and llm-inclusive sets never regress each other.

With ``--include-llm`` (ADR 0145 point 5), a bounded, deterministic
subsample of pairs (``--llm-pair-limit``) is additionally scored
through the contextual-orchestrator adjudication channel -- each pair
costs one provider call -- and the 4-channel estimate is persisted as
the `channel_set_with_llm` set, leaving the deterministic set intact.
Fails closed: with `fast_mlsirm` not importable, a degenerate sample,
or the orchestrator unreachable, nothing is written and the exit is an
explicit error, never a fabricated weight.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os

import asyncpg

from backend.app.config import load_settings
from backend.app.lineage_ingestion import records_from_source_posts
from backend.app.post_eligibility import SOURCE_POST_ELIGIBILITY_SQL
from lineageweave.adjudication_client import ContextualOrchestratorAdjudicationClient
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

DETERMINISTIC_SET_CODE = "channel_set_deterministic"
WITH_LLM_SET_CODE = "channel_set_with_llm"


def _first_env(*names: str) -> str:
    return next((os.environ.get(name, "").strip() for name in names if os.environ.get(name, "").strip()), "")


def sample_pair_scores(
    records: list, *, window: int = DEFAULT_CANDIDATE_WINDOW
) -> tuple[list[dict[str, float]], list[int], list[tuple[str, str]]]:
    """Score every in-window candidate pair, grouped as reconstruct groups.

    Pure so the sampling geometry itself is unit-testable: pairs come
    only from within one group, only from the trailing ``window`` of
    temporally prior records -- the exact candidate set
    ``reconstruct._reconstruct_group`` would consider. Also returns each
    pair's (candidate_label, record_label) so an llm pass can score the
    same pairs without re-deriving the geometry.
    """
    groups: dict[str, list] = {}
    for record in records:
        groups.setdefault(record.group_key, []).append(record)

    pair_scores: list[dict[str, float]] = []
    group_ids: list[int] = []
    pair_labels: list[tuple[str, str]] = []
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
                pair_labels.append((candidate.label, record.label))
    return pair_scores, group_ids, pair_labels


def subsample_stride(total: int, limit: int) -> list[int]:
    """Deterministic, evenly-spread pair indices for the bounded llm pass.

    A stride subsample keeps every reconstruction group represented in
    proportion (pairs are ordered group-by-group) without any randomness
    that would make re-runs incomparable.
    """
    if total <= limit:
        return list(range(total))
    stride = total / limit
    return [min(int(index * stride), total - 1) for index in range(limit)]


async def persist_estimate(
    conn: asyncpg.Connection,
    estimate: ChannelWeightEstimate,
    channel_set_code: str,
) -> None:
    """Replace one channel set's persisted weights atomically."""
    async with conn.transaction():
        await conn.execute(
            "delete from lineage_channel_weight where channel_set_code = $1",
            channel_set_code,
        )
        for channel, weight in estimate.weights.items():
            await conn.execute(
                """
                insert into lineage_channel_weight
                    (channel_set_code, channel_code, weight_value,
                     estimation_method_code, sample_pair_count)
                values ($1, $2, $3, $4, $5)
                """,
                channel_set_code,
                channel,
                weight,
                estimate.estimation_method_code,
                estimate.sample_pair_count,
            )


async def _run(args: argparse.Namespace) -> dict[str, object]:
    settings = load_settings()
    llm_client = None
    if args.include_llm:
        base_url = _first_env("ORCHESTRATOR_BASE_URL", "LLM_GATEWAY_API_URL", "LLM_GATEWAY_URL")
        api_key = _first_env("ORCHESTRATOR_API_KEY", "CONTEXTUAL_ORCHESTRATOR_TOKEN")
        if not base_url or not api_key:
            raise RuntimeError(
                "--include-llm requires ORCHESTRATOR_BASE_URL and "
                "ORCHESTRATOR_API_KEY (or CONTEXTUAL_ORCHESTRATOR_TOKEN)"
            )
        llm_client = ContextualOrchestratorAdjudicationClient(base_url, api_key)

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
            pair_scores, group_ids, pair_labels = sample_pair_scores(records)

            if llm_client is None:
                estimate = estimate_channel_weights(pair_scores, group_ids)
                channel_set_code = DETERMINISTIC_SET_CODE
                llm_scored_pairs = 0
            else:
                chosen = subsample_stride(len(pair_scores), args.llm_pair_limit)
                llm_pairs: list[dict[str, float]] = []
                llm_group_ids: list[int] = []
                for index in chosen:
                    candidate_label, record_label = pair_labels[index]
                    llm_pairs.append(
                        {
                            **pair_scores[index],
                            "llm": llm_client.judge(candidate_label, record_label),
                        }
                    )
                    llm_group_ids.append(group_ids[index])
                estimate = estimate_channel_weights(llm_pairs, llm_group_ids)
                channel_set_code = WITH_LLM_SET_CODE
                llm_scored_pairs = len(chosen)

            if estimate is None:
                raise RuntimeError(
                    "no grounded estimate was produced (fast_mlsirm unavailable, "
                    "sample too small, or a channel was degenerate) -- nothing "
                    "was written; product reconstruction stays fail-closed until "
                    "an estimate is persisted"
                )
            if not args.dry_run:
                await persist_estimate(conn, estimate, channel_set_code)
            return {
                "weights": estimate.weights,
                "channel_set_code": channel_set_code,
                "sample_pair_count": estimate.sample_pair_count,
                "llm_scored_pairs": llm_scored_pairs,
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
        "--include-llm",
        action="store_true",
        help=(
            "Also score a bounded pair subsample through the "
            "contextual-orchestrator adjudication channel and persist the "
            "4-channel set (channel_set_with_llm)"
        ),
    )
    parser.add_argument(
        "--llm-pair-limit",
        type=int,
        default=400,
        help="Maximum pairs scored through the llm channel (default: 400)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Estimate and report, but persist nothing",
    )
    args = parser.parse_args()
    if args.post_limit < 1:
        parser.error("--post-limit must be positive")
    if args.llm_pair_limit < 1:
        parser.error("--llm-pair-limit must be positive")
    print(json.dumps(asyncio.run(_run(args)), ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
