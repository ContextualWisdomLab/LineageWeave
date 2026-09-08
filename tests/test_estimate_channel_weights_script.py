"""Tests for scripts/estimate_channel_weights.py (ADR 0200).

`sample_pair_scores` must reproduce reconstruct's own candidate
geometry -- within-group only, trailing-window only -- because weights
estimated over a different pair population would ground nothing. The
persistence contract must stamp full per-run provenance, and the
snapshot digest must be reproducible so the provenance row names the
exact corpus slice without storing content.
"""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone

import pytest

from lineageweave.channel_weight_estimation import ChannelWeightEstimate
from lineageweave.models import Record

import scripts.estimate_channel_weights as script


def _record(record_id: str, group: str, minute: int, secondary: str = "") -> Record:
    """Build one deterministic source-post record fixture."""
    return Record(
        record_id,
        group,
        f"title {record_id}",
        datetime(2026, 1, 1) + timedelta(minutes=minute),
        secondary,
    )


def test_sampling_stays_within_groups_and_window() -> None:
    """Keep sampled pairs within group and candidate-window boundaries."""
    lineage_records = [
        _record("a1", "g-a", 0),
        _record("a2", "g-a", 1),
        _record("b1", "g-b", 2),
    ]
    pair_scores, group_ids, pair_labels = script.sample_pair_scores(
        lineage_records, candidate_window=50
    )
    # Only a1->a2 pairs up; b1 is alone in its group and never crosses.
    assert len(pair_scores) == 1
    assert group_ids == [0]
    assert set(pair_scores[0]) == {"temporal", "secondary_key", "text"}
    # Labels align with the scored pair so the queued llm judging pass can
    # score the same candidate geometry without re-deriving it.
    assert pair_labels == [("title a1", "title a2")]


def test_sampling_window_bounds_candidates_like_reconstruct() -> None:
    """Match reconstruction candidate-window bounds."""
    lineage_records = [_record(f"r{index}", "g", index) for index in range(5)]
    _, unbounded_ids, _ = script.sample_pair_scores(
        lineage_records, candidate_window=50
    )
    assert len(unbounded_ids) == 4 + 3 + 2 + 1
    pair_scores, _, _ = script.sample_pair_scores(lineage_records, candidate_window=2)
    # Each record sees at most its two immediate predecessors.
    assert len(pair_scores) == 1 + 2 + 2 + 2


def test_llm_subsample_stride_is_deterministic_and_spread() -> None:
    """Keep LLM subsampling deterministic and distributed."""
    # Small totals pass through untouched; larger ones are evenly strided
    # (first index 0, no index past the end, exactly the limit chosen)
    # with no randomness, so re-runs stay comparable.
    assert script.subsample_stride(3, 10) == [0, 1, 2]
    chosen = script.subsample_stride(1000, 40)
    assert len(chosen) == 40
    assert chosen[0] == 0
    assert chosen == sorted(chosen)
    assert chosen[-1] <= 999
    assert script.subsample_stride(1000, 40) == chosen


def test_snapshot_digest_is_reproducible_and_order_sensitive() -> None:
    """Require reproducible order-sensitive source digests."""
    source_post_rows = [
        {"post_id": "a", "created_at": datetime(2026, 1, 1, tzinfo=timezone.utc)},
        {"post_id": "b", "created_at": datetime(2026, 1, 2, tzinfo=timezone.utc)},
    ]
    first = script.source_snapshot_digest(source_post_rows)
    assert first == script.source_snapshot_digest(list(source_post_rows))
    assert first != script.source_snapshot_digest(list(reversed(source_post_rows)))
    assert len(first) == 64


class _Connection:
    def __init__(self) -> None:
        """Initialize the estimation database test double."""
        self.executed: list[tuple[str, tuple[object, ...]]] = []

    @asynccontextmanager
    async def transaction(self):
        """Return the transaction test double context."""
        yield self

    async def execute(self, query: str, *args: object) -> str:
        """Record one persistence statement and its arguments."""
        self.executed.append((" ".join(query.split()), args))
        return "OK"


def test_persist_estimate_stamps_full_provenance_on_one_scoped_set(
    monkeypatch,
) -> None:
    """Persist complete provenance for one scoped estimate set."""
    monkeypatch.setattr(script, "estimator_version", lambda: "0.9.1")
    database_connection = _Connection()
    channel_weight_estimate = ChannelWeightEstimate(
        weights={"temporal": 0.25, "text": 0.75},
        sample_pair_count=600,
        estimation_method_code="mls2plm_expected_information",
    )
    knowledge_cutoff = datetime(2026, 1, 2, tzinfo=timezone.utc)
    estimation_run_id = asyncio.run(
        script.persist_estimate(
            database_connection,
            channel_weight_estimate,
            channel_set_code=script.DETERMINISTIC_SET_CODE,
            snapshot_sha256="a" * 64,
            knowledge_cutoff=knowledge_cutoff,
        )
    )
    delete_query, delete_args = database_connection.executed[0]
    # Scoped delete: persisting the deterministic set must never wipe
    # another set -- each active-channel combination owns its own rows.
    assert (
        "delete from lineage_channel_weight where channel_set_code = $1" in delete_query
    )
    assert delete_args == (script.DETERMINISTIC_SET_CODE,)
    inserted = {call[1][1]: call[1] for call in database_connection.executed[1:]}
    assert set(inserted) == {"temporal", "text"}
    for persisted_row in inserted.values():
        assert persisted_row[0] == script.DETERMINISTIC_SET_CODE
        assert persisted_row[3] == estimation_run_id
        assert persisted_row[4] == "mls2plm_expected_information"
        assert isinstance(persisted_row[5], str) and persisted_row[5].strip()
        assert persisted_row[6] == script.UNANCHORED_METHOD_CODE
        assert persisted_row[7] == "a" * 64
        assert persisted_row[8] == 600
        assert persisted_row[9] == knowledge_cutoff
    assert inserted["text"][2] == 0.75


def test_main_rejects_nonpositive_post_limit(monkeypatch) -> None:
    """Reject a nonpositive command post limit."""
    monkeypatch.setattr(
        "sys.argv", ["estimate_channel_weights.py", "--post-limit", "0"]
    )
    with pytest.raises(SystemExit):
        script.main()
