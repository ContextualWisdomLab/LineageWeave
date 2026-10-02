"""Release identity must stay synchronized across public package surfaces."""

from __future__ import annotations

import json
import tomllib
from pathlib import Path

import lineageweave


def test_release_versions_match() -> None:
    """Expose one version through Python, package metadata, and the frontend."""
    root = Path(__file__).resolve().parents[1]
    project_version = tomllib.loads(
        (root / "pyproject.toml").read_text(encoding="utf-8")
    )["project"]["version"]
    frontend_version = json.loads(
        (root / "frontend" / "package.json").read_text(encoding="utf-8")
    )["version"]

    assert lineageweave.__version__ == project_version == frontend_version
