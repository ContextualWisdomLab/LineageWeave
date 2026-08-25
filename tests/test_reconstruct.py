from __future__ import annotations

from datetime import datetime

from lineageweave import Record, reconstruct
from lineageweave.fixtures import sample_records

def test_reconstruct_finds_the_designed_branch_point(estimated_fixture_weights) -> None:
    """fixtures.sample_records() deliberately makes rec-002 fork into two
    threads (the revised quote, and the delivery question) -- the
    reconstruction must recover that shape without being told about it.
    """
    trees = reconstruct(sample_records(), weights=estimated_fixture_weights)
    tree_a = next(t for t in trees if t.group_key == "A-100")

    assert "rec-001" in tree_a.roots
    assert "rec-002" in tree_a.branch_points()
    assert set(tree_a.children_of["rec-002"]) >= {"rec-003", "rec-004"}


def test_reconstruct_leaves_unrelated_records_as_their_own_root(
    estimated_fixture_weights,
) -> None:
    """rec-006 shares no topic or project code with anything in A-100 and
    should not be force-attached to the best of a set of weak candidates.
    """
    trees = reconstruct(sample_records(), weights=estimated_fixture_weights)
    tree_a = next(t for t in trees if t.group_key == "A-100")

    assert "rec-006" in tree_a.roots


def test_reconstruct_groups_are_independent(estimated_fixture_weights) -> None:
    trees = reconstruct(sample_records(), weights=estimated_fixture_weights)
    tree_b = next(t for t in trees if t.group_key == "B-200")

    assert set(tree_b.records.keys()) == {"rec-101", "rec-102", "rec-103"}
    assert "rec-101" in tree_b.roots


def test_llm_channel_is_dropped_not_faked_when_unavailable(
    estimated_fixture_weights,
) -> None:
    trees = reconstruct(sample_records(), weights=estimated_fixture_weights)
    tree_a = next(t for t in trees if t.group_key == "A-100")

    for edge in tree_a.edges:
        assert "llm" not in edge.channel_scores


class _StubAdjudicationClient:
    available = True

    def __init__(self) -> None:
        self.calls = 0

    def judge(self, candidate_label: str, record_label: str) -> float:
        self.calls += 1
        return float(candidate_label == record_label)


def test_llm_channel_is_scored_during_zero_weight_ablation(
    estimated_fixture_weights,
) -> None:
    stub = _StubAdjudicationClient()
    # Zero is an exact exclusion ablation, not a guessed relative weight:
    # fast-mlsirm supplies every active fusion coefficient under test.
    weights = {**estimated_fixture_weights, "llm": 0.0}
    trees = reconstruct(
        sample_records(), llm=stub, weights=weights
    )
    tree_a = next(t for t in trees if t.group_key == "A-100")

    assert stub.calls > 0
    assert all("llm" in edge.channel_scores for edge in tree_a.edges)


def test_candidate_window_bounds_which_priors_are_considered(
    estimated_fixture_weights,
) -> None:
    records = [
        Record(f"r{i}", "G", f"record {i}", datetime(2026, 1, 1, i), "") for i in range(5)
    ]
    trees = reconstruct(records, weights=estimated_fixture_weights, candidate_window=1)
    tree = trees[0]

    for edge in tree.edges:
        parent_index = int(edge.parent_id[1:])
        child_index = int(edge.child_id[1:])
        assert child_index - parent_index == 1
