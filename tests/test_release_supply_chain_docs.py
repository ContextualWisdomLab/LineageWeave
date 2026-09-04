"""Contract tests for release supply-chain documentation."""

from pathlib import Path


_REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
_ADR = _REPOSITORY_ROOT / "docs" / "adr" / "0361-immutable-release-supply-chain-boundary.md"
_RELEASE_GUIDE = _REPOSITORY_ROOT / "docs" / "release.md"
_DOCTORING = _REPOSITORY_ROOT / "docs" / "doctoring" / "RELEASE_SUPPLY_CHAIN_REFERENCES.md"
_IMMUTABILITY_ENDPOINT = "GET /repos/{owner}/{repo}/immutable-releases"
_EXACT_ARTIFACT_OWNER_SHA = "bd866a21cca2a7e709f0b7a88150c310a9d98239"


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


def test_annotated_release_tag_is_peeled_to_the_exact_source_commit() -> None:
    """Do not compare an annotated tag-object SHA directly with the source commit SHA."""
    for path in (_ADR, _RELEASE_GUIDE):
        text = path.read_text(encoding="utf-8").lower()
        assert "annotated tag" in text, path
        assert "tag object" in text, path
        assert "peel" in text, path
        assert "type `commit`" in text, path
        assert "exact protected source sha" in text, path


def test_prepublication_abort_has_identity_safe_cleanup_before_same_version_retry() -> None:
    """Do not orphan or unsafely reuse a draft release identity after an aborted publish."""
    for path in (_ADR, _RELEASE_GUIDE):
        text = path.read_text(encoding="utf-8").lower()
        assert "pre-publication abort" in text, path
        assert "draft" in text and "unpublished" in text, path
        assert "delete" in text and "candidate tag" in text, path
        assert "re-resolve" in text and "absent" in text, path
        assert "quarantine" in text and "version" in text, path
        assert "never reuse" in text and "published immutable release" in text, path


def test_release_contract_pins_the_repaired_canonical_attestation_owner() -> None:
    """Consume the merged acyclic handoff by immutable owner SHA, never mutable main or the old blocker."""
    for path in (_ADR, _RELEASE_GUIDE, _DOCTORING):
        text = path.read_text(encoding="utf-8")
        assert _EXACT_ARTIFACT_OWNER_SHA in text, path
        assert ".github#1791" in text, path
        assert ".github#1782 remains open" not in text, path

    release_text = _RELEASE_GUIDE.read_text(encoding="utf-8")
    assert (
        "ContextualWisdomLab/.github/.github/workflows/"
        "exact-artifact-sbom-attestation.yml@" + _EXACT_ARTIFACT_OWNER_SHA
    ) in release_text
