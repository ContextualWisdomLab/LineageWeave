"""ADR and release-identity regression for grouping-comparison axis singular values."""

from __future__ import annotations

import json
import re
import tomllib
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
_ADR_DIRECTORY = _ROOT / "docs" / "adr"


def test_axis_singular_decision_uses_unclaimed_proposed_adr_0370() -> None:
    """Keep the reconstructed axis-singular decision off historical ADR 0294."""
    canonical = _ADR_DIRECTORY / "0370-leftover-map-compare-axis-singular.md"

    assert canonical.exists(), "axis-singular decision must use unclaimed ADR 0370"
    content = canonical.read_text(encoding="utf-8")
    assert content.startswith("# ADR 0370 —")
    assert "**Decision status:** Proposed" in content
    assert "**Decision status:** Accepted" not in content
    assert "v2.56.0" in content


def test_axis_singular_release_identity_is_2560_everywhere() -> None:
    """Keep the reconstructed feature on one unreleased product identity."""
    project = tomllib.loads((_ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    frontend = json.loads((_ROOT / "frontend" / "package.json").read_text(encoding="utf-8"))
    runtime = (_ROOT / "lineageweave" / "__init__.py").read_text(encoding="utf-8")
    lock = tomllib.loads((_ROOT / "uv.lock").read_text(encoding="utf-8"))
    locked_lineageweave = [
        package for package in lock["package"] if package.get("name") == "lineageweave"
    ]
    match = re.search(r'^__version__ = "([^"]+)"$', runtime, flags=re.MULTILINE)

    assert match is not None
    assert project["project"]["version"] == "2.56.0"
    assert frontend["version"] == "2.56.0"
    assert match.group(1) == "2.56.0"
    assert len(locked_lineageweave) == 1
    assert locked_lineageweave[0]["version"] == "2.56.0"
