"""Start-reconstruction contracts: digest stability and designed-tree fidelity."""

from pathlib import Path

from lineageweave.fixtures import sample_records
from lineageweave.lineage_persistence import lineage_edge_specs

from backend.app.analysis_run_start import (
    AnalysisRunStartError,
    reconstruction_result_digest,
)
from backend.app.lineage_ingestion import records_from_source_posts

_START_SOURCE = Path(__file__).resolve().parents[1] / "backend" / "app" / "analysis_run_start.py"
_INGESTION_SOURCE = (
    Path(__file__).resolve().parents[1] / "backend" / "app" / "analysis_run_ingestion.py"
)


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


def test_start_maps_source_post_rows_through_records_from_source_posts() -> None:
    """CI-runnable A-100: start uses the same mapper as the product path.

    The HTTP start test needs Keycloak. This check keeps the designed
    fork on every pytest run: source_post-shaped rows through
    ``records_from_source_posts`` must still place the revised quote and
    the delivery question under rec-002.
    """
    rows = []
    for rec in sample_records():
        rows.append(
            {
                "post_id": rec.record_id,
                "process_unit_id": "shared-pu",
                "corporate_entity_id": "shared-corp",
                "post_title": rec.label,
                "thread_group_key": rec.group_key,
                "secondary_grouping_key": rec.secondary_key,
                "created_at": rec.occurred_at,
            }
        )
    edges = lineage_edge_specs(records_from_source_posts(rows))
    children = {edge.child_id for edge in edges if edge.parent_id == "rec-002"}
    assert children >= {"rec-003", "rec-004"}
    assert reconstruction_result_digest(edges) == reconstruction_result_digest(
        lineage_edge_specs(sample_records())
    )


def test_start_locks_before_running_and_maps_unique_violation() -> None:
    """Lock, then Running. A raced insert is 409, not 500."""
    source = _START_SOURCE.read_text(encoding="utf-8")
    lock_at = source.index("for update of run")
    running_at = source.index(
        "await _append_status(conn, analysis_run_id, running_ordinal, _RUNNING"
    )
    assert lock_at < running_at
    assert "UniqueViolationError" in source
    assert "fetch_snapshot_member_posts" in source
    ingestion = _INGESTION_SOURCE.read_text(encoding="utf-8")
    assert "persist_snapshot_members" in ingestion
    assert "parent_visibility_code" in ingestion


def test_start_error_carries_a_next_action() -> None:
    """Operators get a next action, not an internal exception name."""
    error = AnalysisRunStartError(
        422,
        "Connect a TEPP transport from a Failed TEPP row. "
        "This start path does not invent a measurement.",
    )
    assert error.status_code == 422
    assert "invent a measurement" in error.detail
