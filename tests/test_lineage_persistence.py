"""The persistence contract must carry the designed A-100 fork.

If lineage_edge_specs dropped a reconstruct edge, the Event Lineage
panel would stay empty even when reconstruct itself is correct.
"""

from __future__ import annotations

from lineageweave.fixtures import sample_records
from lineageweave.lineage_persistence import lineage_edge_specs


def test_persisted_edges_include_the_designed_a100_fork() -> None:
    edges = lineage_edge_specs(sample_records())
    pairs = {(edge.parent_id, edge.child_id) for edge in edges}
    assert ("rec-002", "rec-003") in pairs
    assert ("rec-002", "rec-004") in pairs
    assert all(edge.fused_score > 0 for edge in edges)


def test_unrelated_rec006_is_not_forced_onto_a_parent() -> None:
    edges = lineage_edge_specs(sample_records())
    children = {edge.child_id for edge in edges}
    assert "rec-006" not in children
