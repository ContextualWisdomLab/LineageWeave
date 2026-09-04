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


def _between(text: str, start_marker: str, end_marker: str) -> str:
    """Return one named procedure slice instead of accepting document-wide keywords."""
    start = text.lower().index(start_marker.lower())
    end = text.lower().index(end_marker.lower(), start)
    return text[start:end].lower()


def test_release_publication_requires_owner_enforced_github_release_immutability() -> None:
    """Keep the immutability admission predicate in one ordered preflight step."""
    for path in (_ADR, _RELEASE_GUIDE):
        text = path.read_text(encoding="utf-8")
        preflight = _numbered_step(
            text,
            10 if path == _RELEASE_GUIDE else 7,
            11 if path == _RELEASE_GUIDE else 8,
        )
        assert _IMMUTABILITY_ENDPOINT.lower() in preflight, path
        assert "enabled: true" in preflight, path
        assert "enforced_by_owner: true" in preflight, path
        assert "fail closed" in preflight, path


def test_release_publication_rechecks_exact_draft_tag_assets_and_immutability_at_boundary() -> None:
    """Bind the final publish decision to one exact draft, tag, asset set and immutable policy."""
    for path in (_ADR, _RELEASE_GUIDE):
        text = path.read_text(encoding="utf-8")
        publish_step = _numbered_step(
            text,
            12 if path == _RELEASE_GUIDE else 8,
            13 if path == _RELEASE_GUIDE else 9,
        )
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


def test_prepublication_abort_orders_identity_proof_before_conditional_tag_cleanup() -> None:
    """Exact candidate ownership must be proved before compare-and-delete or quarantine."""
    adr_text = _ADR.read_text(encoding="utf-8")
    release_text = _RELEASE_GUIDE.read_text(encoding="utf-8")
    abort_procedures = (
        (_ADR, _numbered_step(adr_text, 9, 10), "protected namespace"),
        (
            _RELEASE_GUIDE,
            _between(
                release_text,
                "A failure after step 11 but before publication is a **pre-publication abort**",
                "Never reuse a tag name that has been associated with a published immutable release",
            ),
            "protected tag namespace",
        ),
    )

    for path, procedure, protected_marker in abort_procedures:
        proof_terms = (
            "exact release id",
            "draft: true",
            "prerelease: false",
            "tag_name",
            "asset",
            "digest",
            "recorded tag object" if path == _ADR else "recorded candidate tag object",
        )
        proof_end = max(procedure.index(term) for term in proof_terms)
        compare_delete = procedure.index("compare-and-delete")
        trusted_writer = procedure.index("trusted release writer", compare_delete)
        protected_tag = procedure.index(protected_marker, trusted_writer)
        recorded_tag_object = procedure.index("recorded tag-object sha", protected_tag)
        serialization = procedure.index("serialization", recorded_tag_object)
        quarantine = procedure.index("quarantine", serialization)

        assert (
            proof_end
            < compare_delete
            < trusted_writer
            < protected_tag
            < recorded_tag_object
            < serialization
            < quarantine
        ), path
        assert "do not delete" in procedure[serialization:quarantine], path
        assert "re-resolve" in procedure[compare_delete:], path
        assert "absent" in procedure[compare_delete:], path


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
