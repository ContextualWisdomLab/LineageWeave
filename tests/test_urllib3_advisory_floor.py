"""Reject urllib3 locks affected by the reviewed October 2026 advisories."""

from __future__ import annotations

import tomllib
from pathlib import Path

from packaging.version import Version


def test_locked_urllib3_excludes_reviewed_vulnerable_releases() -> None:
    """GHSA-8988-9cw3-xx77, gh4c-6fx4-qh6g, vxq7-64xx-v4gw fix at 2.8.0."""
    lock = tomllib.loads(
        (Path(__file__).resolve().parents[1] / "uv.lock").read_text()
    )
    versions = [
        Version(package["version"])
        for package in lock["package"]
        if package["name"] == "urllib3"
    ]
    assert versions, "uv.lock must retain the existing urllib3 dependency"
    assert all(version >= Version("2.8.0") for version in versions)
