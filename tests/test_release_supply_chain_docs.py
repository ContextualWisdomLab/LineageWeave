"""Contract tests for release supply-chain documentation."""

from pathlib import Path


_REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
_ADR = _REPOSITORY_ROOT / "docs" / "adr" / "0358-immutable-release-supply-chain-boundary.md"
_RELEASE_GUIDE = _REPOSITORY_ROOT / "docs" / "release.md"
_IMMUTABILITY_ENDPOINT = "GET /repos/{owner}/{repo}/immutable-releases"


def test_release_publication_requires_enabled_github_release_immutability() -> None:
    """Fail closed before publication unless GitHub release immutability is enabled."""
    for path in (_ADR, _RELEASE_GUIDE):
        text = path.read_text(encoding="utf-8")
        assert _IMMUTABILITY_ENDPOINT in text, path
        assert "fail closed" in text.lower(), path
        assert "before tag" in text.lower(), path


def test_release_publication_rechecks_immutability_and_tag_identity_at_publish_boundary() -> None:
    """Close the preflight-to-publish TOCTOU window for immutable release identity."""
    for path in (_ADR, _RELEASE_GUIDE):
        text = path.read_text(encoding="utf-8").lower()
        assert "immediately before publish" in text, path
        assert "recheck" in text, path
        assert "tag" in text and "source sha" in text, path
