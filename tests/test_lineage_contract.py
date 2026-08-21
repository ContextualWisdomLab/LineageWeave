"""Synthetic contract tests for the reusable Naruon provider boundary."""

import json
from datetime import UTC, datetime, timedelta

import pytest

import lineageweave.lineage_contract as contract
from lineageweave.adjudication_client import NullAdjudicationClient
from lineageweave.lineage_contract import (
    EmailEvidence,
    LineageAnalysisPolicy,
    LineageAnalysisRequest,
    LineageEvidenceRecord,
    LineageProjectHint,
    analyze_lineage,
)
from lineageweave.models import Edge, Record, Tree

BASE_TIME = datetime(2026, 1, 1, 9, tzinfo=UTC)


def evidence(
    ref: str,
    *,
    available_at: datetime = BASE_TIME,
    occurred_at: datetime = BASE_TIME,
    label: str = "HVDC design review",
) -> LineageEvidenceRecord:
    """Create a bounded synthetic record without real organization data."""
    return LineageEvidenceRecord(
        evidence_ref=ref,
        group_key="synthetic-customer",
        label=label,
        occurred_at=occurred_at,
        available_at=available_at,
        secondary_key="project-01",
        body_text="Confirm drawing revision and delivery date.",
    )


def request(records: tuple[LineageEvidenceRecord, ...], **kwargs) -> LineageAnalysisRequest:
    """Build a valid synthetic request with explicit authorization scope."""
    values = {
        "analysis_id": "analysis-001",
        "authorization_scope_ref": "scope-opaque-001",
        "knowledge_cutoff": BASE_TIME + timedelta(hours=1),
    }
    values.update(kwargs)
    return LineageAnalysisRequest(evidence=records, **values)


def test_request_json_keeps_email_protocol_evidence_separate_and_deterministic() -> None:
    """RFC/thread fields are preserved as a separate evidence object."""
    record = evidence("mail-001")
    record = LineageEvidenceRecord(
        **{**record.__dict__, "email": EmailEvidence(rfc_message_id="<synthetic-001@example.invalid>")}
    )
    first = request((record,))

    payload = json.loads(first.canonical_json())

    assert first.request_digest() == request((record,)).request_digest()
    assert payload["contract_version"] == "lineage-analysis/v1"
    assert payload["evidence"][0]["email"]["rfc_message_id"] == "<synthetic-001@example.invalid>"
    assert "truth_status" not in payload["evidence"][0]["email"]


def test_request_rejects_empty_and_oversized_text() -> None:
    """Opaque identifiers and text fields stay bounded at the trust boundary."""
    with pytest.raises(ValueError, match="analysis_id must be a non-empty string"):
        request((evidence("text-001"),), analysis_id="").validate()
    with pytest.raises(ValueError, match="analysis_id exceeds"):
        request((evidence("text-001"),), analysis_id="x" * 201).validate()
    too_long_body = LineageEvidenceRecord(**{**evidence("text-002").__dict__, "body_text": "x" * 4_001})
    with pytest.raises(ValueError, match="body_text exceeds"):
        request((too_long_body,)).validate()
    too_long_secondary = LineageEvidenceRecord(**{**evidence("text-003").__dict__, "secondary_key": "x" * 201})
    with pytest.raises(ValueError, match="secondary_key exceeds"):
        request((too_long_secondary,)).validate()


def test_request_rejects_unbound_hints_excess_records_and_policy_budget() -> None:
    """Hints and work budgets cannot escape the submitted authorization scope."""
    with pytest.raises(ValueError, match="outside the request"):
        request(
            (evidence("hint-001"),),
            project_hints=(LineageProjectHint("missing-001", "project-001", "Missing"),),
        ).validate()
    with pytest.raises(ValueError, match="exceeds max_evidence_records"):
        request(
            (evidence("count-001"), evidence("count-002")),
            policy=LineageAnalysisPolicy(max_evidence_records=1),
        ).validate()
    with pytest.raises(ValueError, match="max_body_chars must be between"):
        request((evidence("policy-001"),), policy=LineageAnalysisPolicy(max_body_chars=8_001)).validate()


def test_request_rejects_unbounded_nested_collections() -> None:
    """Nested evidence collections cannot bypass the request work budget."""
    with pytest.raises(ValueError, match="project_hints exceeds max_project_hints"):
        request(
            (evidence("hint-budget-001"),),
            project_hints=(
                LineageProjectHint("hint-budget-001", "project-001", "one"),
                LineageProjectHint("hint-budget-001", "project-002", "two"),
            ),
            policy=LineageAnalysisPolicy(max_project_hints=1),
        ).validate()

    record = LineageEvidenceRecord(
        **{
            **evidence("email-budget-001").__dict__,
            "email": EmailEvidence(references=("ref-001", "ref-002")),
        }
    )
    with pytest.raises(ValueError, match="evidence.email.references exceeds the 1-item limit"):
        request((record,), policy=LineageAnalysisPolicy(max_email_refs_per_record=1)).validate()


def test_policy_rejects_nested_collection_limits_above_contract_ceiling() -> None:
    """Policy fields cannot raise the nested collection ceilings at runtime."""
    with pytest.raises(ValueError, match="max_project_hints must be between"):
        request((evidence("hint-ceiling-001"),), policy=LineageAnalysisPolicy(max_project_hints=501)).validate()
    with pytest.raises(ValueError, match="max_email_refs_per_record must be between"):
        request(
            (evidence("email-ceiling-001"),),
            policy=LineageAnalysisPolicy(max_email_refs_per_record=65),
        ).validate()


def test_request_validates_email_collections_and_policy_lower_bound() -> None:
    """Participant, attachment, and lower-bound policy values remain valid inputs."""
    record = evidence("email-collections")
    record = LineageEvidenceRecord(
        **{
            **record.__dict__,
            "body_text": "",
            "email": EmailEvidence(
                references=("<parent@example.invalid>",),
                participant_refs=("participant-001",),
                attachment_refs=("attachment-001",),
            ),
        }
    )
    request((record,), policy=LineageAnalysisPolicy(max_body_chars=0)).validate()


def test_analyze_lineage_excludes_late_evidence_and_exposes_unavailable_llm() -> None:
    """Later-available evidence cannot influence a cutoff-bound result."""
    late = evidence("late-001", available_at=BASE_TIME + timedelta(hours=2))
    result = analyze_lineage(request((evidence("early-001"), late)))

    serialized = result.to_json()

    assert "late-001" not in serialized
    assert any(item.code == "evidence_after_cutoff_excluded" for item in result.limitations)
    assert any(item.code == "llm_channel_unavailable" for item in result.limitations)
    assert all(
        edge.parent_evidence_ref != "late-001" and edge.child_evidence_ref != "late-001"
        for edge in result.edges
    )


def test_analyze_lineage_reports_an_explicitly_unavailable_llm() -> None:
    """An explicit unavailable client follows the same fail-closed path as no client."""
    result = analyze_lineage(
        request((evidence("explicit-null-llm-001"),)),
        llm=NullAdjudicationClient(),
    )

    assert any(item.code == "llm_channel_unavailable" for item in result.limitations)


def test_analyze_lineage_accepts_an_available_llm_without_candidates() -> None:
    """An available client is not marked unavailable when no judgment is needed."""
    class AvailableClient:
        """Minimal available client for the one-record no-candidate path."""

        available = True

    result = analyze_lineage(
        request((evidence("available-llm-001"),)),
        llm=AvailableClient(),
    )

    assert not any(item.code == "llm_channel_unavailable" for item in result.limitations)


def test_analyze_lineage_excludes_events_that_occur_after_the_cutoff() -> None:
    """An early import cannot make a future event visible in a past analysis."""
    future_event = evidence(
        "future-event-001",
        occurred_at=BASE_TIME + timedelta(hours=2),
        available_at=BASE_TIME,
    )

    result = analyze_lineage(request((evidence("early-001"), future_event)))

    serialized = result.to_json()
    assert "future-event-001" not in serialized
    assert any(item.code == "evidence_after_cutoff_excluded" for item in result.limitations)


def test_analyze_lineage_maps_edges_to_opaque_refs_and_project_hints_stay_non_authoritative() -> None:
    """The existing reconstruction is reused without creating project authority."""
    records = (evidence("source-001"), evidence("source-002", occurred_at=BASE_TIME + timedelta(hours=1)))
    result = analyze_lineage(
        request(
            records,
            project_hints=(LineageProjectHint("source-001", "project-opaque", "Design review"),),
        )
    )

    assert all(
        edge.parent_evidence_ref in {"source-001", "source-002"}
        and edge.child_evidence_ref in {"source-001", "source-002"}
        for edge in result.edges
    )
    assert result.edges
    assert json.loads(result.to_json())["edges"]
    assert any(item.code == "project_hints_are_non_authoritative" for item in result.limitations)


@pytest.mark.parametrize(
    ("mutator", "message"),
    [
        (lambda records: (records[0], records[0]), "evidence_ref values must be unique"),
        (lambda records: (LineageEvidenceRecord(**{**records[0].__dict__, "available_at": BASE_TIME.replace(tzinfo=None)}),), "timezone-aware"),
    ],
)
def test_request_rejects_duplicate_or_ambiguous_evidence(mutator, message: str) -> None:
    """Trust-boundary validation rejects identity collisions and naive clocks."""
    records = (evidence("duplicate-001"), evidence("duplicate-002"))
    with pytest.raises(ValueError, match=message):
        request(mutator(records)).validate()


def test_policy_rejects_unbounded_record_budget() -> None:
    """A provider request cannot silently opt into unbounded work."""
    with pytest.raises(ValueError, match="between 1 and 5000"):
        request((evidence("bounded-001"),), policy=LineageAnalysisPolicy(max_evidence_records=0)).validate()


def test_analyze_lineage_drops_an_unexpected_edge_reference(monkeypatch) -> None:
    """The response boundary cannot leak an edge outside cutoff-eligible refs."""
    def fake_reconstruct(records: list[Record], *, llm) -> list[Tree]:
        """Return a deliberately malformed internal edge for boundary testing."""
        return [
            Tree(
                group_key=records[0].group_key,
                records={record.record_id: record for record in records},
                edges=[Edge("late-001", records[0].record_id, 0.9, {"text": 0.9})],
                roots=[],
                children_of={},
            )
        ]

    monkeypatch.setattr(contract, "reconstruct", fake_reconstruct)
    result = analyze_lineage(request((evidence("early-001"),)))

    assert result.edges == ()
