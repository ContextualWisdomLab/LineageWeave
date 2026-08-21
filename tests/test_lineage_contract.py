"""Synthetic contract tests for the reusable Naruon provider boundary."""

import json
from datetime import UTC, datetime, timedelta

import pytest

from lineageweave.lineage_contract import (
    EmailEvidence,
    LineageAnalysisPolicy,
    LineageAnalysisRequest,
    LineageEvidenceRecord,
    LineageProjectHint,
    analyze_lineage,
)

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
    return LineageAnalysisRequest(
        analysis_id="analysis-001",
        authorization_scope_ref="scope-opaque-001",
        knowledge_cutoff=BASE_TIME + timedelta(hours=1),
        evidence=records,
        **kwargs,
    )


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
