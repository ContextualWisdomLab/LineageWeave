"""Tests for ADR 0145's fail-closed channel-weight boundary."""

from __future__ import annotations

import pytest

from lineageweave.channel_weight_estimation import estimate_channel_weights


def test_misaligned_inputs_are_a_caller_bug_not_missing_data() -> None:
    with pytest.raises(ValueError):
        estimate_channel_weights([{"temporal": 0.5}], [0, 1])


def test_unanchored_channel_scores_never_run_a_fit(monkeypatch) -> None:
    import fast_mlsirm

    def unexpected_fit(**_kwargs):
        raise AssertionError("an unanchored fit cannot establish genuine lineage")

    monkeypatch.setattr(fast_mlsirm, "fit", unexpected_fit)
    pairs = [
        {
            "temporal": 0.9 if index % 2 else 0.1,
            "secondary_key": 0.9 if index % 3 else 0.1,
            "text": 0.9 if index % 5 else 0.1,
        }
        for index in range(200)
    ]

    assert (
        estimate_channel_weights(pairs, [index % 4 for index in range(len(pairs))])
        is None
    )
