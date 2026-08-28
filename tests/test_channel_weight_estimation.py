"""Tests for the fail-closed channel-weight boundary."""

from __future__ import annotations

import pytest

from lineageweave.channel_weight_estimation import (
    estimate_channel_weights,
    estimate_fixture_channel_weights,
)
from scripts.seed_demo_data import demo_channel_weight_estimate


def test_owner_artifact_absence_never_produces_local_weights() -> None:
    pairs = [{"temporal": 0.2, "text": 0.8}, {"temporal": 0.8, "text": 0.2}]
    assert estimate_channel_weights(pairs, [0, 1]) is None
    assert estimate_fixture_channel_weights() is None


def test_demo_seed_drops_unavailable_lineage_without_aborting() -> None:
    """The real seed boundary returns unavailable instead of terminating."""

    assert demo_channel_weight_estimate() is None


def test_misaligned_inputs_are_rejected_before_fail_closed_return() -> None:
    with pytest.raises(ValueError, match="must align"):
        estimate_channel_weights([{"temporal": 0.5}], [0, 1])
    with pytest.raises(ValueError, match="same channel set"):
        estimate_channel_weights([{"temporal": 0.5}, {"text": 0.5}], [0, 1])
