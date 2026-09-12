from __future__ import annotations

import json
import re
from pathlib import Path


_REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
_FRONTEND_PACKAGE = _REPOSITORY_ROOT / "frontend" / "package.json"
_FRONTEND_LOCK = _REPOSITORY_ROOT / "frontend" / "pnpm-lock.yaml"
_VITEST_4_PATCHED_MINIMUM = (4, 1, 11)


def _manifest_vitest_version() -> tuple[int, int, int]:
    manifest = json.loads(_FRONTEND_PACKAGE.read_text(encoding="utf-8"))
    specifier = manifest["devDependencies"]["vitest"]
    match = re.search(r"(\d+)\.(\d+)\.(\d+)", specifier)
    assert match is not None, f"unparseable Vitest requirement: {specifier!r}"
    return tuple(int(part) for part in match.groups())


def test_vitest_requirement_is_on_the_patched_v4_line() -> None:
    """Keep the supported Vitest 4 toolchain outside GHSA-82fw-gwwq-j7x9."""
    version = _manifest_vitest_version()

    # A major-line change needs a separate compatibility decision; this repair
    # deliberately targets Vitest's patched 4.1.11+ line rather than 5.x prereleases.
    assert version[0] == 4
    assert version >= _VITEST_4_PATCHED_MINIMUM


def test_pnpm_lock_has_no_vulnerable_vitest_4_1_10_nodes() -> None:
    """Require the generated lock graph to move both Vitest and its mocker."""
    lock_text = _FRONTEND_LOCK.read_text(encoding="utf-8")

    assert "vitest@4.1.10" not in lock_text
    assert "@vitest/mocker@4.1.10" not in lock_text
