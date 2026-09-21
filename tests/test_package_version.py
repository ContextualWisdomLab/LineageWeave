"""Release identity stays consistent across Python and frontend artifacts."""

from __future__ import annotations

import json
import tomllib
from pathlib import Path

from lineageweave import __version__


def test_release_versions_are_synchronized() -> None:
    """Runtime provenance must use the same version as shipped package metadata."""
    repository_root = Path(__file__).resolve().parents[1]
    project = tomllib.loads((repository_root / "pyproject.toml").read_text(encoding="utf-8"))
    frontend = json.loads(
        (repository_root / "frontend" / "package.json").read_text(encoding="utf-8")
    )

    assert __version__ == project["project"]["version"] == frontend["version"]
