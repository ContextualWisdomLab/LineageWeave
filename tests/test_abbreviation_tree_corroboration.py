"""Tree-constrained Searxng abbreviation cross-check (ADR 0033)."""

from __future__ import annotations

import pytest

from lineageweave.abbreviation_tree_corroboration import (
    AbbreviationTreeMatch,
    TreeEntityCandidate,
    abbreviation_candidates,
    corroborate_abbreviation_against_tree,
    exact_catalog_matches,
)
from lineageweave.relation_verification import (
    STATUS_CORROBORATED,
    STATUS_PENDING,
    STATUS_UNCORROBORATED,
    NullRelationVerificationClient,
    RelationVerificationResult,
)

_TREE = (
    TreeEntityCandidate("group-id", "Demo Group"),
    TreeEntityCandidate("corp-id", "Demo Corp"),
    TreeEntityCandidate("plant-id", "Demo Plant"),
)


class _FakeVerificationClient:
    available = True

    def __init__(self, hits: dict[tuple[str, str], RelationVerificationResult]) -> None:
        self._hits = hits
        self.calls: list[tuple[str, str]] = []

    def verify(self, organization_name: str, relationship_label: str) -> RelationVerificationResult:
        self.calls.append((organization_name, relationship_label))
        return self._hits.get(
            (organization_name, relationship_label),
            RelationVerificationResult(STATUS_UNCORROBORATED, None),
        )


class _RaisingVerificationClient:
    available = True

    def verify(self, organization_name: str, relationship_label: str) -> RelationVerificationResult:
        raise RuntimeError("searxng timeout")


def test_exact_catalog_name_is_not_an_abbreviation_candidate() -> None:
    assert abbreviation_candidates(("Demo Corp", "DC", "  "), _TREE) == ("DC",)


def test_tied_exact_catalog_names_stay_candidates() -> None:
    twins = (
        TreeEntityCandidate("a", "Demo Twin"),
        TreeEntityCandidate("b", "Demo Twin"),
    )
    assert abbreviation_candidates(("Demo Twin",), twins) == ("Demo Twin",)


def test_unique_searxng_hit_binds_the_tree_node() -> None:
    client = _FakeVerificationClient(
        {
            ("Demo Corp", "DC"): RelationVerificationResult(
                STATUS_CORROBORATED, "https://example.test/demo-corp-dc"
            )
        }
    )
    match = corroborate_abbreviation_against_tree("DC", _TREE, client)
    assert match == AbbreviationTreeMatch(
        raw_organization_name="DC",
        corporate_entity_id="corp-id",
        verification_status_code=STATUS_CORROBORATED,
        verification_evidence_url="https://example.test/demo-corp-dc",
    )
    assert ("Demo Group", "DC") in client.calls
    assert ("Demo Plant", "DC") in client.calls


def test_no_searxng_hit_stays_unbound() -> None:
    match = corroborate_abbreviation_against_tree("ZZ", _TREE, _FakeVerificationClient({}))
    assert match.corporate_entity_id is None
    assert match.verification_status_code == STATUS_UNCORROBORATED
    assert match.verification_evidence_url is None


def test_tied_searxng_hits_stay_unbound() -> None:
    client = _FakeVerificationClient(
        {
            ("Demo Corp", "DX"): RelationVerificationResult(
                STATUS_CORROBORATED, "https://example.test/demo-corp"
            ),
            ("Demo Group", "DX"): RelationVerificationResult(
                STATUS_CORROBORATED, "https://example.test/demo-group"
            ),
        }
    )
    match = corroborate_abbreviation_against_tree("DX", _TREE, client)
    assert match.corporate_entity_id is None
    assert match.verification_status_code == STATUS_UNCORROBORATED


def test_unavailable_searxng_is_pending_and_does_not_invent_a_parent() -> None:
    match = corroborate_abbreviation_against_tree("DC", _TREE, NullRelationVerificationClient())
    assert match.corporate_entity_id is None
    assert match.verification_status_code == STATUS_PENDING
    assert match.verification_evidence_url is None


def test_empty_mention_is_uncorroborated() -> None:
    match = corroborate_abbreviation_against_tree("  ", _TREE, _FakeVerificationClient({}))
    assert match.corporate_entity_id is None
    assert match.verification_status_code == STATUS_UNCORROBORATED


def test_search_failure_is_not_recorded_as_uncorroborated() -> None:
    with pytest.raises(RuntimeError, match="searxng timeout"):
        corroborate_abbreviation_against_tree("DC", _TREE, _RaisingVerificationClient())


def test_exact_catalog_matches_normalize_legal_suffix() -> None:
    matches = exact_catalog_matches("Demo Corp.", _TREE)
    assert [row.entity_id for row in matches] == ["corp-id"]


def test_exact_catalog_matches_ignore_empty_normalized_names() -> None:
    assert exact_catalog_matches("   ", _TREE) == ()
    assert exact_catalog_matches("Corp.", _TREE) == ()
