"""Repository-wide pytest collection hooks for optional backend extras."""

from __future__ import annotations

from pathlib import Path

from lineageweave.optional_extra_collection import (
    collection_path_requires_missing_extras,
    missing_optional_extra_modules,
)


def pytest_ignore_collect(collection_path: Path, config: object) -> bool:
    """Skip files that import optional extras the sandbox did not install."""
    del config
    return collection_path_requires_missing_extras(
        collection_path,
        missing_optional_extra_modules(),
    )
