"""Consumer contract for the released fast-mlsirm owner dependency."""

from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).parents[1]
PYPROJECT = ROOT / "pyproject.toml"
UV_LOCK = ROOT / "uv.lock"
OWNER_RELEASE_VERSION = "0.9.1"
OWNER_RELEASE_COMMIT = "09f762ded35786dd1078222a4577ff09d649816f"
STALE_CONSUMER_COMMIT = "d025b7d237d8db7ca97a5611606c6285d5870895"


def test_backend_extra_consumes_exact_released_fast_mlsirm_owner_commit() -> None:
    """Keep psychometric code owner-pinned to the immutable v0.9.1 release target."""
    pyproject = PYPROJECT.read_text(encoding="utf-8")
    assert STALE_CONSUMER_COMMIT not in pyproject
    assert (
        "fast-mlsirm @ git+https://github.com/ContextualWisdomLab/fast-mlsirm.git@"
        f"{OWNER_RELEASE_COMMIT}"
    ) in pyproject


def test_universal_lock_matches_the_released_fast_mlsirm_owner_identity() -> None:
    """Require the generated lock to preserve the same owner version and commit."""
    lock = UV_LOCK.read_text(encoding="utf-8")
    assert STALE_CONSUMER_COMMIT not in lock
    package_marker = (
        '[[package]]\nname = "fast-mlsirm"\n'
        f'version = "{OWNER_RELEASE_VERSION}"\n'
    )
    assert package_marker in lock
    assert OWNER_RELEASE_COMMIT in lock
