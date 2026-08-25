"""Shared evidence-backed test fixtures."""

import pytest

from lineageweave.channel_weight_estimation import estimate_fixture_channel_weights


@pytest.fixture(scope="session")
def estimated_fixture_weights() -> dict[str, float]:
    """Return one Rust-backed estimate for reconstruction tests."""
    estimate = estimate_fixture_channel_weights()
    assert estimate is not None
    return estimate.weights
