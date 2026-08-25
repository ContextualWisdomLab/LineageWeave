"""Repository-wide pytest collection hooks for optional backend extras."""

from __future__ import annotations

from pathlib import Path

import pytest

from lineageweave.channel_weight_estimation import estimate_fixture_channel_weights
from lineageweave.optional_extra_collection import (
    collection_path_requires_missing_extras,
    missing_optional_extra_modules,
)


@pytest.fixture(scope="session")
def estimated_fixture_weights() -> dict[str, float]:
    """Return one Rust-backed estimate for reconstruction tests."""
    estimate = estimate_fixture_channel_weights()
    if estimate is None:
        pytest.skip("fast_mlsirm unavailable -- install the Rust-backed org package")
    return estimate.weights


def pytest_ignore_collect(collection_path: Path, config: object) -> bool | None:
    """Skip files that import optional extras the sandbox did not install."""
    del config
    if collection_path_requires_missing_extras(
        collection_path,
        missing_optional_extra_modules(),
    ):
        return True
    return None
