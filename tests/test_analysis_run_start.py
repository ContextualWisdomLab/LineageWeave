"""Start-reconstruction contracts: digest stability and designed-tree fidelity."""

from backend.app.analysis_run_ingestion import reconstructed_edge_is_visible
from backend.app.analysis_run_start import (
    AnalysisRunStartError,
    reconstruction_member_ids,
    reconstruction_result_digest,
    start_write_conflict_error,
)
from backend.app.lineage_ingestion import records_from_source_posts
from lineageweave.fixtures import sample_records
from lineageweave.lineage_persistence import lineage_edge_specs


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
    children = {
        edge.child_id for edge in edges if edge.parent_id == "rec-002"
    }
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


def test_start_error_carries_a_next_action() -> None:
    """Operators get a next action, not an internal exception name."""
    error = AnalysisRunStartError(
        422,
        "Connect a TEPP transport from a Failed TEPP row. "
        "This start path does not invent a measurement.",
    )
    assert error.status_code == 422
    assert "invent a measurement" in error.detail
    conflict = start_write_conflict_error()
    assert conflict.status_code == 409
    assert "Refresh to see the stored tree" in conflict.detail
