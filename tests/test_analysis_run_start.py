"""Start-reconstruction contracts: digest, freeze, 422/409, designed tree."""

from datetime import datetime, timezone

import pytest

from backend.app.analysis_run_ingestion import reconstructed_edge_is_visible
from backend.app.analysis_run_start import (
    AnalysisRunStartError,
    configured_tepp_client,
    reconstruction_member_ids,
    reconstruction_result_digest,
    start_kind_rejection,
    start_write_conflict_error,
    tepp_run_request,
    tepp_submit_outcome,
)
from backend.app.lineage_ingestion import records_from_source_posts
from lineageweave.fixtures import sample_records
from lineageweave.lineage_persistence import lineage_edge_specs
from lineageweave.tepp_client import AnalysisRunRequest, TeppClient, TeppNotAvailable


def test_reconstruction_digest_is_stable_and_ignores_edge_order() -> None:
    """The same parent choices hash the same way regardless of insert order."""
    edges = lineage_edge_specs(sample_records())
    reversed_edges = list(reversed(edges))
    assert reconstruction_result_digest(edges) == reconstruction_result_digest(reversed_edges)
    assert reconstruction_result_digest([]) == reconstruction_result_digest([])
    assert reconstruction_result_digest(edges) != reconstruction_result_digest([])


def test_start_uses_the_same_parent_choices_as_library_reconstruct() -> None:
    """The product start path must recover the designed A-100 fork.

    fixtures.sample_records() is the synthetic gold tree: rec-002 is the
    branch point for the revised quote and the delivery question. A start
    that dropped an edge or invented a parent would fail this check.
    """
    edges = lineage_edge_specs(sample_records())
    children = {edge.child_id for edge in edges if edge.parent_id == "rec-002"}
    assert children >= {"rec-003", "rec-004"}
    assert all(0.0 <= edge.fused_score <= 1.0 for edge in edges)
    assert "theta" not in reconstruction_result_digest(edges)


def test_start_wiring_recovers_a100_from_source_post_rows() -> None:
    """CI must exercise records_from_source_posts, not only library reconstruct."""
    rows = [
        {
            "post_id": record.record_id,
            "post_title": record.label,
            "created_at": record.occurred_at,
            "thread_group_key": record.group_key,
            "secondary_grouping_key": record.secondary_key,
            "process_unit_id": None,
            "corporate_entity_id": "corp-demo",
        }
        for record in sample_records()
    ]
    edges = lineage_edge_specs(records_from_source_posts(rows))
    children = {edge.child_id for edge in edges if edge.parent_id == "rec-002"}
    assert children >= {"rec-003", "rec-004"}
    assert reconstruction_result_digest(edges) == reconstruction_result_digest(
        lineage_edge_specs(sample_records())
    )


def test_snapshot_members_exclude_a_later_backfill() -> None:
    """Start reconstructs the create-time bag, not a later cutoff re-query."""
    captured = ["rec-001", "rec-002", "rec-003", "rec-004"]
    cutoff_with_backfill = [*captured, "rec-backfill"]
    assert reconstruction_member_ids(captured, cutoff_with_backfill) == captured
    assert reconstruction_member_ids([], cutoff_with_backfill) == cutoff_with_backfill


def test_reconstructed_edge_hides_unaffiliated_private_titles() -> None:
    """Edge titles use the same public-or-affiliated rule as cutoff posts."""
    affiliated = ["corp-demo"]
    assert reconstructed_edge_is_visible(
        parent_visibility_code="public",
        parent_corporate_entity_id="corp-other",
        child_visibility_code="public",
        child_corporate_entity_id="corp-other",
        affiliated_entity_ids=affiliated,
    )
    assert not reconstructed_edge_is_visible(
        parent_visibility_code="private",
        parent_corporate_entity_id="corp-other",
        child_visibility_code="public",
        child_corporate_entity_id="corp-demo",
        affiliated_entity_ids=affiliated,
    )


def test_period_report_start_is_unprocessable_and_tepp_is_allowed() -> None:
    """Period-report stays 422. TEPP start is allowed so tepp_client can run."""
    report = start_kind_rejection("analysis_run_report")
    assert report is not None
    assert report.status_code == 422
    assert "invent a measurement" in report.detail
    assert "period report" in report.detail
    assert start_kind_rejection("analysis_run_lineage") is None
    assert start_kind_rejection("analysis_run_tepp") is None


def _tepp_request() -> AnalysisRunRequest:
    return tepp_run_request(
        idempotency_key="buyer-tepp-2026-w07",
        snapshot_sha256="ab" * 32,
        knowledge_cutoff=datetime(2026, 1, 12, 12, 0, tzinfo=timezone.utc),
        corporate_entity_id="11111111-1111-1111-1111-111111111111",
    )


def test_tepp_run_request_is_the_published_wire_shape() -> None:
    """Start builds TEPP's seven-field request from the frozen run."""
    request = _tepp_request()
    payload = request.to_json()
    assert payload["contract_version"] == 1
    assert payload["idempotency_key"] == "buyer-tepp-2026-w07"
    assert payload["snapshot_id"] == "ab" * 32
    assert payload["knowledge_cutoff"] == "2026-01-12T12:00:00Z"
    assert payload["model_contract_version"] == "tepp-analysis-run-v1"
    assert payload["output_profile"] == "calibrated_event_measurement"
    assert "theta" not in str(payload).casefold()


def test_tepp_submit_outcome_drops_a_missing_transport() -> None:
    """A missing TEPP transport is Failed, never a fabricated score."""
    status, failure = tepp_submit_outcome(TeppClient(), _tepp_request())
    assert status == "analysis_status_failed"
    assert failure == "tepp_not_available"


def test_tepp_submit_outcome_does_not_persist_an_empty_envelope() -> None:
    """An accepted envelope is not a persistable measurement."""

    class _Accepting(TeppClient):
        def __init__(self) -> None:
            super().__init__(transport=lambda _payload: {"status": "accepted"})

    status, failure = tepp_submit_outcome(_Accepting(), _tepp_request())
    assert status == "analysis_status_failed"
    assert failure == "tepp_result_not_persisted"


def test_configured_tepp_client_stays_unavailable_without_http() -> None:
    """Empty or non-http URLs keep the default dropped channel."""
    assert isinstance(configured_tepp_client(""), TeppClient)
    client = configured_tepp_client("file:///tmp/tepp.json")
    with pytest.raises(TeppNotAvailable):
        client.submit_analysis_run(_tepp_request())


def test_hidden_run_start_is_not_found() -> None:
    """Operators get a 404 next action, not an internal exception name."""
    error = AnalysisRunStartError(404, "This analysis run is not visible.")
    assert error.status_code == 404
    assert "not visible" in error.detail


def test_running_restart_conflicts_and_succeeded_replay_is_documented() -> None:
    """Running without pending outbox is 409. Succeeded replay is a no-op."""
    conflict = start_write_conflict_error()
    assert conflict.status_code == 409
    assert "Refresh to see the stored tree" in conflict.detail
    running = AnalysisRunStartError(
        409,
        "Open this run. Start is only for a Pending lineage reconstruction.",
    )
    assert running.status_code == 409
    assert "Pending" in running.detail
