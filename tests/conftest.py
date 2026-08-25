"""Shared evidence-backed test fixtures."""

import pytest

from lineageweave.channel_weight_estimation import estimate_fixture_channel_weights


@pytest.fixture(scope="session")
def estimated_fixture_weights() -> dict[str, float]:
    """Return one Rust-backed estimate for reconstruction tests."""
    estimate = estimate_fixture_channel_weights()
    if estimate is None:
        pytest.skip("fast_mlsirm unavailable -- install the Rust-backed org package")
    return estimate.weights
