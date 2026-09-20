"""Dependency and verifier contracts for the PyJWT security floor."""

from __future__ import annotations

import re
import tomllib
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MINIMUM_PYJWT_VERSION = (2, 13, 0)


def _version_tuple(version: str) -> tuple[int, int, int]:
    """Parse the repository's numeric PyJWT version contract."""
    match = re.fullmatch(r"(\d+)\.(\d+)\.(\d+)", version)
    assert match is not None, f"unexpected PyJWT version syntax: {version!r}"
    return tuple(int(part) for part in match.groups())


def test_declared_pyjwt_floor_excludes_known_vulnerable_versions() -> None:
    """Both install surfaces must require the first release with the 2026 JWT fixes."""
    project = tomllib.loads((ROOT / "pyproject.toml").read_text())
    extras = project["project"]["optional-dependencies"]

    for extra_name in ("dev", "backend"):
        requirements = [
            requirement
            for requirement in extras[extra_name]
            if requirement.lower().startswith("pyjwt[crypto]")
        ]
        assert requirements == ["pyjwt[crypto]>=2.13.0"], (
            f"{extra_name} must fail closed below PyJWT 2.13.0; got {requirements!r}"
        )


def test_locked_pyjwt_satisfies_the_security_floor() -> None:
    """The committed resolver state must not reintroduce a vulnerable PyJWT."""
    lock = tomllib.loads((ROOT / "uv.lock").read_text())
    versions = [
        package["version"]
        for package in lock["package"]
        if package["name"].lower() == "pyjwt"
    ]

    assert versions, "uv.lock must contain PyJWT"
    assert all(_version_tuple(version) >= MINIMUM_PYJWT_VERSION for version in versions)


def test_owned_jwt_verifiers_do_not_mix_symmetric_and_asymmetric_families() -> None:
    """Owned JWT verification paths stay RS256-only instead of admitting HS/RS confusion."""
    for relative_path in ("backend/app/auth.py", "scripts/smoke_test_oidc.py"):
        source = (ROOT / relative_path).read_text()
        algorithm_lists = re.findall(r"algorithms\s*=\s*\[([^\]]+)\]", source)
        assert algorithm_lists, f"{relative_path} must declare an explicit JWT algorithm allow-list"
        assert all(re.fullmatch(r'\s*["\']RS256["\']\s*', value) for value in algorithm_lists), (
            f"{relative_path} must not mix HMAC and asymmetric JWT algorithm families"
        )
