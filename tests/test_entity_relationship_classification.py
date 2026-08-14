"""Tests for lineageweave.entity_relationship_classification.

parse_classification_response's tests need no live provider. The
real-provider test is skipped unless LINEAGEWEAVE_TEST_ORCHESTRATOR_BASE_URL/
_API_KEY are set (same env vars keyman_extraction's real-provider test
uses), and runs against fixtures.ambiguous_entity_relationship_post() --
an organization that is genuinely both a customer and a competitor in the
same post, so a keyword-matcher would get it wrong.
"""

from __future__ import annotations

import os

import pytest

from lineageweave.entity_relationship_classification import (
    VOC,
    VOCO,
    VOS,
    ContextualOrchestratorEntityRelationshipClient,
    NullEntityRelationshipClient,
    parse_classification_response,
)


def test_null_relationship_client_is_unavailable_not_empty_relations() -> None:
    client = NullEntityRelationshipClient()
    assert client.available is False
    with pytest.raises(RuntimeError):
        client.classify("any title", "any body", ["Acme Corp"])
from lineageweave.fixtures import ambiguous_entity_relationship_post


def test_parses_a_well_formed_json_array() -> None:
    content = (
        '[{"organization_name": "Acme Corp", "relationship_type_code": "rel_voc"}, '
        '{"organization_name": "Bolt Supply", "relationship_type_code": "rel_vos"}]'
    )
    results = parse_classification_response(content, ["Acme Corp", "Bolt Supply"])
    assert {r.organization_name: r.relationship_type_code for r in results} == {
        "Acme Corp": "rel_voc",
        "Bolt Supply": "rel_vos",
    }


def test_entry_naming_an_organization_not_in_the_input_list_is_skipped() -> None:
    content = '[{"organization_name": "Unlisted Corp", "relationship_type_code": "rel_voc"}]'
    assert parse_classification_response(content, ["Acme Corp"]) == []


def test_entry_with_invalid_relationship_code_is_skipped() -> None:
    content = '[{"organization_name": "Acme Corp", "relationship_type_code": "not_a_real_code"}]'
    assert parse_classification_response(content, ["Acme Corp"]) == []


def test_empty_array_is_no_relationships() -> None:
    assert parse_classification_response("[]", ["Acme Corp"]) == []


def test_invalid_json_returns_empty_list() -> None:
    assert parse_classification_response("not json", ["Acme Corp"]) == []


_ORCHESTRATOR_BASE_URL = os.environ.get("LINEAGEWEAVE_TEST_ORCHESTRATOR_BASE_URL")
_ORCHESTRATOR_API_KEY = os.environ.get("LINEAGEWEAVE_TEST_ORCHESTRATOR_API_KEY")


@pytest.mark.skipif(
    not (_ORCHESTRATOR_BASE_URL and _ORCHESTRATOR_API_KEY),
    reason="set LINEAGEWEAVE_TEST_ORCHESTRATOR_BASE_URL and LINEAGEWEAVE_TEST_ORCHESTRATOR_API_KEY to run",
)
def test_contextual_orchestrator_classifies_a_dual_role_organization() -> None:
    """A real LLM call against a genuinely hard case: Meridian Utilities is
    both a repeat customer (transformer line) and a new competitor
    (switchgear division bidding against us) in the SAME post -- a
    keyword-matcher scanning for "customer" vs. "competitor" language
    would likely pick whichever word appears, not reason about which
    relationship the post is actually about. Colby Insulation is the
    unambiguous supplier case (the "vos" edge case the product brief
    calls out as uncommon but real).
    """
    client = ContextualOrchestratorEntityRelationshipClient(
        base_url=_ORCHESTRATOR_BASE_URL, api_key=_ORCHESTRATOR_API_KEY
    )
    title, body, organization_names = ambiguous_entity_relationship_post()

    results = client.classify(title, body, organization_names)

    by_name = {r.organization_name: r.relationship_type_code for r in results}
    assert set(by_name) == {"Meridian Utilities", "Colby Insulation"}
    # Meridian is defensibly either reading (customer-of-record placing the
    # order, or the newly-competing division) -- the real assertion is that
    # the model picked ONE of the two relationships the text actually
    # describes, not something unrelated.
    assert by_name["Meridian Utilities"] in {VOC, VOCO}
    assert by_name["Colby Insulation"] == VOS


def test_classified_names_attach_cataloged_org_ids_or_stay_null() -> None:
    """A resolved counterparty keeps its cataloged id; an unmatched name
    stays null -- never a guessed neighborhood for the related walk.
    """
    from backend.app.entity_relationship_ingestion import attach_resolved_entity_ids
    from lineageweave.corporate_hierarchy_resolution import CorporateEntityCandidate

    rows = attach_resolved_entity_ids(
        [
            {"counterparty_entity_name": "Demo Corp", "relationship_type_code": "rel_voc"},
            {"counterparty_entity_name": "Northridge Grid", "relationship_type_code": "rel_voc"},
        ],
        [
            CorporateEntityCandidate("corp-1", "Demo Corp"),
            CorporateEntityCandidate("corp-2", "Test Corp"),
        ],
    )
    by_name = {row["counterparty_entity_name"]: row["corporate_entity_id"] for row in rows}
    assert by_name["Demo Corp"] == "corp-1"
    assert by_name["Northridge Grid"] is None
