"""Searxng hits stay 미검증 후보 until a unique catalog attach."""

from lineageweave.corporate_hierarchy_resolution import CorporateEntityCandidate
from lineageweave.unverified_candidates import (
    ATTACH_MISS_NEXT_ACTION,
    ATTACH_TIE_NEXT_ACTION,
    UNVERIFIED_CANDIDATE_LABEL,
    attach_unverified_candidate,
    candidate_payloads,
    candidates_from_search_results,
    stub_unverified_candidate,
    wants_outside_verification,
)


def test_search_hits_are_labeled_unverified() -> None:
    candidates = candidates_from_search_results(
        "Demo Corp",
        [{"title": "Demo Corp parent note", "url": "https://demo.example/parent", "content": "demo corp"}],
    )
    assert candidates[0].status_label == UNVERIFIED_CANDIDATE_LABEL
    assert candidates[0].promote_destination == "customers"
    payload = candidate_payloads(candidates)
    assert payload[0]["status_label"] == "미검증 후보"


def test_stub_candidate_does_not_search_the_public_web() -> None:
    candidates = stub_unverified_candidate("Demo Corp")
    assert candidates[0].status_label == UNVERIFIED_CANDIDATE_LABEL
    assert candidates[0].evidence_url is None
    assert candidates[0].promote_destination == "customers"


def test_attach_unique_existing_catalog_row() -> None:
    result = attach_unverified_candidate(
        "Demo Corp",
        [CorporateEntityCandidate("corp-1", "Demo Corp")],
    )
    assert result.attached is True
    assert result.catalog_id == "corp-1"


def test_attach_tie_does_not_create_auto_row() -> None:
    result = attach_unverified_candidate(
        "Demo Corp",
        [
            CorporateEntityCandidate("corp-1", "Demo Corp"),
            CorporateEntityCandidate("corp-2", "Demo Corp"),
        ],
    )
    assert result.attached is False
    assert result.catalog_id is None
    assert result.empty_next_action == ATTACH_TIE_NEXT_ACTION


def test_attach_miss_stays_unbound() -> None:
    result = attach_unverified_candidate(
        "Uncataloged Widget",
        [CorporateEntityCandidate("corp-1", "Demo Corp")],
    )
    assert result.attached is False
    assert result.empty_next_action == ATTACH_MISS_NEXT_ACTION


def test_outside_parent_question_wants_verification() -> None:
    assert wants_outside_verification("실제 부모 조직은 무엇인가요?")
    assert not wants_outside_verification("누가 관련되었나요?")
