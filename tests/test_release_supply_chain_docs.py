"""Contract tests for release supply-chain documentation."""

from pathlib import Path


_REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
_ADR = _REPOSITORY_ROOT / "docs" / "adr" / "0361-immutable-release-supply-chain-boundary.md"
_RELEASE_GUIDE = _REPOSITORY_ROOT / "docs" / "release.md"
_DOCTORING = _REPOSITORY_ROOT / "docs" / "doctoring" / "RELEASE_SUPPLY_CHAIN_REFERENCES.md"
_IMMUTABILITY_ENDPOINT = "GET /repos/{owner}/{repo}/immutable-releases"
_EXACT_ARTIFACT_OWNER_SHA = "bd866a21cca2a7e709f0b7a88150c310a9d98239"


def _numbered_step(text: str, number: int, following: int) -> str:
    """Return one numbered release/decision step so ordering assertions stay local."""
    start = text.index(f"\n{number}. ")
    end = text.index(f"\n{following}. ", start)
    return text[start:end].lower()


def test_release_publication_requires_owner_enforced_github_release_immutability() -> None:
    """Keep the immutability admission predicate in one ordered preflight step."""
    for path in (_ADR, _RELEASE_GUIDE):
        text = path.read_text(encoding="utf-8")
        preflight = _numbered_step(text, 10 if path == _RELEASE_GUIDE else 7, 11 if path == _RELEASE_GUIDE else 8)
        assert _IMMUTABILITY_ENDPOINT.lower() in preflight, path
        assert "enabled: true" in preflight, path
        assert "enforced_by_owner: true" in preflight, path
        assert "fail closed" in preflight, path


def test_release_publication_rechecks_exact_draft_tag_assets_and_immutability_at_boundary() -> None:
    """Bind the final publish decision to one exact draft, tag, asset set and immutable policy."""
    for path in (_ADR, _RELEASE_GUIDE):
        text = path.read_text(encoding="utf-8")
        publish_step = _numbered_step(text, 12 if path == _RELEASE_GUIDE else 8, 13 if path == _RELEASE_GUIDE else 9)
        for required in (
            "immediately before publish",
            "exact release id",
            "draft: true",
            "tag_name",
            "prerelease: false",
            "asset",
            "digest",
            "annotated tag",
            "tag object",
            "peel",
            "type `commit`",
            "exact protected source sha",
        ):
            assert required in publish_step, (path, required)
        assert "enforced_by_owner: true" in publish_step, path
        assert "trusted release writer" in publish_step, path
        assert "fail closed" in publish_step, path


def test_prepublication_abort_has_conditional_tag_cleanup_before_same_version_retry() -> None:
    """Never delete a candidate ref after a stale ownership check."""
    for path in (_ADR, _RELEASE_GUIDE):
        text = path.read_text(encoding="utf-8").lower()
        assert "pre-publication abort" in text, path
        assert "draft" in text and "unpublished" in text, path
        assert "compare-and-delete" in text, path
        assert "trusted release writer" in text, path
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
