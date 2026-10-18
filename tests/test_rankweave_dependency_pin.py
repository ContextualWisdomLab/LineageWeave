"""RankWeave install boundary.

The direct requirement names the canonical owner release. The lock
records the commit that release resolved to, so a retagged release
cannot change an install without a lock update.
"""

from __future__ import annotations

import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RELEASE = "v0.18.0"
COMMIT = "61c49c50d3b4a24fc9bd7c6d3a7f2f4ba19d7be6"
GIT = "https://github.com/ContextualWisdomLab/RankWeave.git"


def _load(name: str) -> dict:
    """Load a TOML document from the repository root."""
    return tomllib.loads((ROOT / name).read_text())


def test_direct_requirement_names_the_canonical_release() -> None:
    """The project dependency names RankWeave by its release tag."""
    project = _load("pyproject.toml")
    rankweave = [
        item
        for item in project["project"]["dependencies"]
        if item.startswith("rankweave ")
    ]
    assert rankweave == [f"rankweave @ git+{GIT}@{RELEASE}"]


def test_lock_binds_the_release_to_the_resolved_commit() -> None:
    """The lock keeps the release tag and the commit it resolved to."""
    lock = _load("uv.lock")
    lineageweave = next(pkg for pkg in lock["package"] if pkg["name"] == "lineageweave")
    requirement = next(
        item
        for item in lineageweave["metadata"]["requires-dist"]
        if item["name"] == "rankweave"
    )
    assert requirement["git"] == f"{GIT}?rev={RELEASE}"

    resolved = next(pkg for pkg in lock["package"] if pkg["name"] == "rankweave")
    assert resolved["version"] == "0.18.0"
    assert resolved["source"]["git"] == f"{GIT}?rev={RELEASE}#{COMMIT}"
