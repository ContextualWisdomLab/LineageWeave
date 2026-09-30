"""Keep every install surface on a PyJWT release outside affected advisories."""

from __future__ import annotations

import re
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PATCHED_VERSION = (2, 14, 0)


def _version_tuple(version: str) -> tuple[int, int, int]:
    match = re.fullmatch(r"(\d+)\.(\d+)\.(\d+)", version)
    assert match is not None, f"unexpected PyJWT version syntax: {version!r}"
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
        assert requirements == ["pyjwt[crypto]>=2.14.0"]


def test_lockfile_contains_only_patched_pyjwt_releases() -> None:
    lock = tomllib.loads((ROOT / "uv.lock").read_text())
    versions = [
        package["version"]
        for package in lock["package"]
        if package["name"].lower() == "pyjwt"
    ]

    assert versions, "uv.lock must contain PyJWT"
    assert all(_version_tuple(version) >= PATCHED_VERSION for version in versions)
