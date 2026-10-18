"""Consumer contract for the released fast-mlsirm owner dependency."""

from __future__ import annotations

from pathlib import Path
import tomllib


ROOT = Path(__file__).parents[1]
PYPROJECT = ROOT / "pyproject.toml"
UV_LOCK = ROOT / "uv.lock"
OWNER_RELEASE_VERSION = "0.9.1"
OWNER_RELEASE_COMMIT = "09f762ded35786dd1078222a4577ff09d649816f"
OWNER_REPOSITORY = "https://github.com/ContextualWisdomLab/fast-mlsirm.git"
STALE_CONSUMER_COMMIT = "d025b7d237d8db7ca97a5611606c6285d5870895"


def test_backend_extra_consumes_exact_released_fast_mlsirm_owner_commit() -> None:
    """Keep psychometric code owner-pinned to the immutable v0.9.1 release target."""
    pyproject = PYPROJECT.read_text(encoding="utf-8")
    assert STALE_CONSUMER_COMMIT not in pyproject
    assert f"fast-mlsirm @ git+{OWNER_REPOSITORY}@{OWNER_RELEASE_COMMIT}" in pyproject


def test_universal_lock_binds_fast_mlsirm_package_to_the_released_owner_source() -> None:
    """Bind version, repository, revision, and resolved commit in one lock record."""
    lock_text = UV_LOCK.read_text(encoding="utf-8")
    assert STALE_CONSUMER_COMMIT not in lock_text

    lock = tomllib.loads(lock_text)
    packages = [
        package
        for package in lock.get("package", [])
        if package.get("name") == "fast-mlsirm"
    ]
    assert len(packages) == 1

    package = packages[0]
    expected_source = (
        f"{OWNER_REPOSITORY}?rev={OWNER_RELEASE_COMMIT}#{OWNER_RELEASE_COMMIT}"
    )
    assert package.get("version") == OWNER_RELEASE_VERSION
    assert package.get("source") == {"git": expected_source}
