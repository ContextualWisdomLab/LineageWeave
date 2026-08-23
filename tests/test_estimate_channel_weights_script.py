"""Tests for scripts/estimate_channel_weights.py's sampling and persistence.

`sample_pair_scores` must reproduce reconstruct's own candidate
geometry -- within-group only, trailing-window only -- because weights
estimated over a different pair population would ground nothing.
"""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from datetime import datetime, timedelta

from lineageweave.channel_weight_estimation import ChannelWeightEstimate
from lineageweave.models import Record

import scripts.estimate_channel_weights as script


def _record(record_id: str, group: str, minute: int, secondary: str = "") -> Record:
    return Record(
        record_id,
        group,
        f"title {record_id}",
        datetime(2026, 1, 1) + timedelta(minutes=minute),
        secondary,
    )


def test_sampling_stays_within_groups_and_window() -> None:
    records = [
        _record("a1", "g-a", 0),
        _record("a2", "g-a", 1),
        _record("b1", "g-b", 2),
    ]
    pair_scores, group_ids = script.sample_pair_scores(records, window=50)
    # Only a1->a2 pairs up; b1 is alone in its group and never crosses.
    assert len(pair_scores) == 1
    assert group_ids == [0]
    assert set(pair_scores[0]) == {"temporal", "secondary_key", "text"}


def test_sampling_window_bounds_candidates_like_reconstruct() -> None:
    records = [_record(f"r{index}", "g", index) for index in range(5)]
    _, unbounded_ids = script.sample_pair_scores(records, window=50)
    assert len(unbounded_ids) == 4 + 3 + 2 + 1
    pair_scores, _ = script.sample_pair_scores(records, window=2)
    # Each record sees at most its two immediate predecessors.
    assert len(pair_scores) == 1 + 2 + 2 + 2


def test_persist_estimate_replaces_the_whole_weight_set() -> None:
    class _Connection:
        def __init__(self) -> None:
            self.executed: list[tuple[str, tuple[object, ...]]] = []

        @asynccontextmanager
        async def transaction(self):
            yield self

        async def execute(self, query: str, *args: object) -> str:
            self.executed.append((" ".join(query.split()), args))
            return "OK"

    conn = _Connection()
    estimate = ChannelWeightEstimate(
        weights={"temporal": 0.25, "text": 0.75},
        sample_pair_count=600,
        estimation_method_code="mls2plm_discrimination",
    )
    asyncio.run(script.persist_estimate(conn, estimate))
    assert "delete from lineage_channel_weight" in conn.executed[0][0]
    inserted = {call[1][0]: call[1] for call in conn.executed[1:]}
    assert set(inserted) == {"temporal", "text"}
    assert inserted["text"][1] == 0.75
    assert inserted["text"][2] == "mls2plm_discrimination"
    assert inserted["text"][3] == 600
