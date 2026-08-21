"""The persistence contract must carry the designed A-100 fork.

If lineage persistence drops a reconstruction edge or its active weighting
profile, the Buyer cannot audit why the Event Lineage relation was selected.
"""

from __future__ import annotations

import math

from lineageweave.fixtures import sample_records
from lineageweave.lineage_persistence import (
    RECONSTRUCTION_VERSION,
    lineage_edge_specs,
    lineage_reconstruction_spec,
)


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


def test_reconstruction_spec_retains_normalized_active_weights_and_version() -> None:
    spec = lineage_reconstruction_spec(sample_records())

    assert spec.reconstruction_version == RECONSTRUCTION_VERSION
    assert set(spec.channel_weights) == {"temporal", "secondary_key", "text"}
    assert "llm" not in spec.channel_weights
    assert math.isclose(sum(spec.channel_weights.values()), 1.0, abs_tol=1e-12)
    assert spec.edges
    for edge in spec.edges:
        contribution = sum(
            edge.channel_scores[channel] * weight
            for channel, weight in spec.channel_weights.items()
        )
        assert math.isclose(contribution, edge.fused_score, abs_tol=1e-12)
