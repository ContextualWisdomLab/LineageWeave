"""RED contracts for the Buyer project-history timeline."""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone

import pytest

from backend.app.project_history import (
    ProjectHistoryConnection,
    fetch_project_history_projection,
)
from lineageweave.project_history import (
    build_project_history_projection,
    classify_project_event,
    normalize_project_key,
    responsibility_transition_code,
)


def _event_row(post_id: str = "00000000-0000-0000-0000-000000000001") -> dict[str, object]:
    """Return one synthetic authorized source row for pure projection tests."""

    return {
        "post_id": post_id,
        "post_title": "Contract awarded",
        "created_at": datetime(2022, 3, 11, 9, tzinfo=timezone.utc),
        "voc_type_code": None,
        "source_stage_code": None,
        "source_detail_state_code": None,
    }


def test_project_identity_is_exact_but_unicode_compatible() -> None:
    """Compatibility forms may normalize; fuzzy project binding may not."""

    assert normalize_project_key("  Ｐ－１００  ") == "p-100"
    assert normalize_project_key("P-100-A") != normalize_project_key("P-100")
    with pytest.raises(ValueError):
        normalize_project_key("   ")


def test_event_display_classification_does_not_create_authority() -> None:
    """The lifecycle label is presentation metadata over an existing post."""

    assert (
        classify_project_event(
            title="Contract awarded",
            source_stage_code=None,
            source_detail_state_code=None,
            voc_type_code=None,
            is_focus=False,
        )
        == "contract_awarded"
    )
    for is_focus in (False, True):
        assert (
            classify_project_event(
                title="Field complaint received",
                source_stage_code=None,
                source_detail_state_code=None,
                voc_type_code="voc",
                is_focus=is_focus,
            )
            == "voc_received"
        )


def test_responsibility_transition_describes_document_evidence_only() -> None:
    """Missing adjacent evidence is a visible evidence gap, not an HR fact."""

    assert responsibility_transition_code(["person:a"], ["person:a"]) == "continuous"
    assert responsibility_transition_code(["person:a"], ["person:b"]) == "handoff"
    assert responsibility_transition_code(["person:a"], []) == "assignment_gap"


def test_matching_observed_project_code_keeps_its_distinct_display_name() -> None:
    """A matching code may carry a human display name that is not itself the key."""

    event_id = "00000000-0000-0000-0000-000000000001"
    projection = build_project_history_projection(
        project_key="P-100",
        focus_event_id=event_id,
        event_rows=[_event_row(event_id)],
        match_rows=[
            {
                "post_id": event_id,
                "match_kind_code": "source_project_code",
                "matched_value": "P-100",
                "confidence": None,
                "ontology_iri": None,
                "provenance": "source_post.source_project_code",
            },
            {
                "post_id": event_id,
                "match_kind_code": "source_project_name",
                "matched_value": "Transformer renewal",
                "confidence": None,
                "ontology_iri": None,
                "provenance": "source_post.source_project_name",
            },
        ],
        role_rows=[],
        edge_rows=[],
    )

    assert projection["project_name"] == "Transformer renewal"
    assert [row["matched_value"] for row in projection["events"][0]["project_matches"]] == [
        "P-100",
        "Transformer renewal",
    ]


def test_summary_responsibilities_remain_inferred_evidence() -> None:
    """LLM-derived summary roles must not become observed or an HR assignment ledger."""

    event_id = "00000000-0000-0000-0000-000000000001"
    projection = build_project_history_projection(
        project_key="P-100",
        focus_event_id=event_id,
        event_rows=[_event_row(event_id)],
        match_rows=[
            {
                "post_id": event_id,
                "match_kind_code": "source_project_code",
                "matched_value": "P-100",
                "confidence": None,
                "ontology_iri": None,
                "provenance": "source_post.source_project_code",
            }
        ],
        role_rows=[
            {
                "post_id": event_id,
                "actor_name": "Synthetic Project Manager",
                "responsibility": "Coordinate the specification revision",
                "actor_type_code": "prov_person",
                "affiliated_organization_name": "Demo Corp",
                "cataloged_person_id": None,
                "cataloged_team_id": None,
                "cataloged_corporate_entity_id": None,
                "truth_status_code": "inferred",
                "provenance": "post_summary_role",
            }
        ],
        edge_rows=[],
    )

    role = projection["events"][0]["responsibility_evidence"][0]
    assert role["truth_status_code"] == "inferred"
    assert role["provenance"] == "post_summary_role"


def test_project_history_connection_protocol_fails_explicitly() -> None:
    """The protocol default is not an executable ellipsis/no-op."""

    async def invoke() -> None:
        await ProjectHistoryConnection.fetch(object(), "select 1")

    with pytest.raises(NotImplementedError):
        asyncio.run(invoke())


def test_invalid_focus_identifier_fails_before_a_database_cast() -> None:
    """A malformed focus identifier must fail closed before reaching PostgreSQL."""

    class FocusConnection:
        def __init__(self) -> None:
            self.calls = 0

        async def fetch(self, query: str, *args: object) -> list[dict[str, object]]:
            self.calls += 1
            if self.calls == 1:
                return [_event_row()]
            raise AssertionError("malformed focus identifier reached a database query")

    connection = FocusConnection()
    with pytest.raises(ValueError, match="focus_post_id"):
        asyncio.run(
            fetch_project_history_projection(
                connection,
                project_key="P-100",
                focus_post_id="not-a-uuid",
                knowledge_cutoff=datetime(2026, 8, 20, tzinfo=timezone.utc),
                corporate_entity_ids=[],
            )
        )
    assert connection.calls == 0
