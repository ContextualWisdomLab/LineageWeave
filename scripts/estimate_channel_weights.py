"""Operator estimation of lineage channel-fusion weights (ADR 0200).

Samples candidate parent-child pairs from the real corpus exactly the
way `reconstruct` forms them (same grouping fallback, same candidate
window), scores each pair on the three deterministic channels, fits
`fast-mlsirm`'s multilevel 2PL over the dichotomized scores, and
persists the normalized expected-information weights into
`lineage_channel_weight` (migration 0200) with full per-run provenance:
run identity, estimator version, anchor method, a reproducible source
snapshot digest, sample size, and the knowledge cutoff.

Persisting is not activating: the product loader refuses every anchor
method until one is authorized under ADR 0200 point 3, so rows written
here are inert evidence until that authorization lands. The llm
channel is deliberately absent -- bulk synchronous provider calls are
banned (operator directive, 2026-08-24); llm pair scoring arrives with
the queued worker (ADR 0200 point 5).

No database connection is held across the scoring/fitting phase
(a reaped idle connection killed an earlier run): one short-lived
connection fetches rows, none is open while fitting, and a fresh one
persists the estimate.
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import uuid
from datetime import datetime

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

DETERMINISTIC_SET_CODE = "channel_set_deterministic"
# ADR 0200 point 3: honest label for an estimate whose latent factor is
# validated only by the channels' internal response structure, pending
# the TEPP criterion-validity gate.
UNANCHORED_METHOD_CODE = "unanchored_internal_structure"


def estimator_version() -> str:
    """The installed fast-mlsirm version, for the persisted provenance."""
    from importlib.metadata import PackageNotFoundError, version

    for name in ("fast-mlsirm", "fast_mlsirm"):
        try:
            return version(name)
        except PackageNotFoundError:
            continue
    import fast_mlsirm

    return str(getattr(fast_mlsirm, "__version__", "unknown"))


def source_snapshot_digest(rows: list) -> str:
    """Reproducible SHA-256 over the ordered sampled (post_id, created_at).

    Two runs that sampled the same posts in the same order produce the
    same digest, so the provenance row names exactly which corpus slice
    supported the estimate without storing any post content.
    """
    material = "\n".join(
        f"{row['post_id']}\t{row['created_at'].isoformat()}" for row in rows
    )
    return hashlib.sha256(material.encode("utf-8")).hexdigest()


def sample_pair_scores(
    records: list, *, window: int = DEFAULT_CANDIDATE_WINDOW
) -> tuple[list[dict[str, float]], list[int], list[tuple[str, str]]]:
    """Score every in-window candidate pair, grouped as reconstruct groups.

    Pure so the sampling geometry itself is unit-testable: pairs come
    only from within one group, only from the trailing ``window`` of
    temporally prior records -- the exact candidate set
    ``reconstruct`` would consider. Also returns each pair's
    (candidate_label, record_label) so the queued llm judging pass can
    score the same candidate geometry without re-deriving it.
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
    *,
    channel_set_code: str,
    snapshot_sha256: str,
    knowledge_cutoff: datetime,
) -> str:
    """Replace one channel set's persisted weights atomically, with provenance.

    Returns the estimation run id stamped on every row of the set.
    """
    estimation_run_id = str(uuid.uuid4())
    version = estimator_version()
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
                     estimation_run_id, estimation_method_code,
                     estimator_version, anchor_method_code,
                     source_snapshot_sha256, sample_pair_count,
                     knowledge_cutoff)
                values ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
                """,
                channel_set_code,
                channel,
                weight,
                estimation_run_id,
                estimate.estimation_method_code,
                version,
                UNANCHORED_METHOD_CODE,
                snapshot_sha256,
                estimate.sample_pair_count,
                knowledge_cutoff,
            )
    return estimation_run_id


async def _run_channel_weight_estimation(
    estimation_arguments: argparse.Namespace,
) -> dict[str, object]:
    """Execute one bounded lineage channel-weight estimation run."""
    settings = load_settings()
    # Short-lived fetch connection; nothing stays open while fitting.
    conn = await asyncpg.connect(settings.database_url)
    try:
        rows = await conn.fetch(
            "select post_id, post_title, voc_type_code, created_at, "
            "corporate_entity_id, process_unit_id, thread_group_key, "
            "secondary_grouping_key "
            f"from source_post where {SOURCE_POST_ELIGIBILITY_SQL.format(alias='source_post')} "
            "order by created_at, post_id limit $1::bigint",
            estimation_arguments.post_limit,
        )
    finally:
        await conn.close()
    if not rows:
        raise RuntimeError(
            "no eligible source posts exist; import a corpus before estimating"
        )
    snapshot_sha256 = source_snapshot_digest(rows)
    knowledge_cutoff = max(row["created_at"] for row in rows)
    records = records_from_source_posts(rows)
    pair_scores, group_ids, _pair_labels = sample_pair_scores(records)

    estimate = estimate_channel_weights(pair_scores, group_ids)
    if estimate is None:
        raise RuntimeError(
            "no grounded estimate was produced (fast_mlsirm unavailable, "
            "sample too small, a channel degenerate, or the fit did not "
            "converge) -- nothing was written; run again after fixing the "
            "named condition"
        )
    estimation_run_id = None
    if not estimation_arguments.dry_run:
        conn = await asyncpg.connect(settings.database_url)
        try:
            estimation_run_id = await persist_estimate(
                conn,
                estimate,
                channel_set_code=DETERMINISTIC_SET_CODE,
                snapshot_sha256=snapshot_sha256,
                knowledge_cutoff=knowledge_cutoff,
            )
        finally:
            await conn.close()
    return {
        "weights": estimate.weights,
        "channel_set_code": DETERMINISTIC_SET_CODE,
        "sample_pair_count": estimate.sample_pair_count,
        "estimation_method_code": estimate.estimation_method_code,
        "anchor_method_code": UNANCHORED_METHOD_CODE,
        "estimation_run_id": estimation_run_id,
        "source_snapshot_sha256": snapshot_sha256,
        "knowledge_cutoff": knowledge_cutoff.isoformat(),
        "persisted": not estimation_arguments.dry_run,
        "activation": (
            "blocked_until_anchor_authorized (ADR 0200 point 3): the "
            "product loader refuses every anchor method today, so these "
            "rows are inert evidence"
        ),
    }


def main() -> None:
    """Validate operator inputs and run the estimation."""
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
    estimation_arguments = parser.parse_args()
    if estimation_arguments.post_limit < 1:
        parser.error("--post-limit must be positive")
    print(
        json.dumps(
            asyncio.run(_run_channel_weight_estimation(estimation_arguments)),
            ensure_ascii=False,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
