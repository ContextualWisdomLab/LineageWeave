"""Keep dependency locks outside the PyJWT and urllib3 advisory ranges."""

from __future__ import annotations

import re
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PYJWT_PATCHED_VERSION = (2, 15, 1)
URLLIB3_PATCHED_VERSION = (2, 8, 0)


def _parse_version_tuple(version: str) -> tuple[int, int, int]:
    match = re.fullmatch(r"(\d+)\.(\d+)\.(\d+)", version)
    assert match is not None, f"unexpected dependency version syntax: {version!r}"
    return tuple(int(part) for part in match.groups())


def test_dev_and_backend_require_the_patched_pyjwt_release() -> None:
    project = tomllib.loads((ROOT / "pyproject.toml").read_text())
    extras = project["project"]["optional-dependencies"]

    for extra_name in ("dev", "backend"):
        requirements = [
            requirement
            for requirement in extras[extra_name]
            if requirement.lower().startswith("pyjwt[crypto]")
        ]
        assert requirements == ["pyjwt[crypto]>=2.15.1"]


def test_lockfile_contains_only_patched_pyjwt_releases() -> None:
    lock = tomllib.loads((ROOT / "uv.lock").read_text())
    versions = [
        package["version"]
        for package in lock["package"]
        if package["name"].lower() == "pyjwt"
    ]

    assert versions, "uv.lock must contain PyJWT"
    assert all(
        _parse_version_tuple(version) >= PYJWT_PATCHED_VERSION
        for version in versions
    )


def test_project_requires_the_patched_urllib3_release() -> None:
    """Make the urllib3 advisory floor explicit instead of transitive."""
    project = tomllib.loads((ROOT / "pyproject.toml").read_text())
    requirements = [
        requirement
        for requirement in project["project"]["dependencies"]
        if requirement.lower().startswith("urllib3")
    ]

    assert requirements == ["urllib3>=2.8.0"]


def test_lockfile_contains_only_patched_urllib3_releases() -> None:
    """Reject urllib3 versions affected by the exact-head Trivy findings."""
    lock = tomllib.loads((ROOT / "uv.lock").read_text())
    versions = [
        package["version"]
        for package in lock["package"]
        if package["name"].lower() == "urllib3"
    ]

    assert versions, "uv.lock must contain urllib3"
    assert all(
        _parse_version_tuple(version) >= URLLIB3_PATCHED_VERSION
        for version in versions
    )
