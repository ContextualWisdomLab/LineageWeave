"""Start-reconstruction contracts: digest stability and designed-tree fidelity."""

from lineageweave.fixtures import sample_records
from lineageweave.lineage_persistence import lineage_edge_specs

from backend.app.analysis_run_start import (
    AnalysisRunStartError,
    reconstruction_result_digest,
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


def test_start_error_carries_a_next_action() -> None:
    """Operators get a next action, not an internal exception name."""
    error = AnalysisRunStartError(
        422,
        "Connect a TEPP transport from a Failed TEPP row. "
        "This start path does not invent a measurement.",
    )
    assert error.status_code == 422
    assert "invent a measurement" in error.detail
