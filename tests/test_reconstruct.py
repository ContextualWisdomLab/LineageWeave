from __future__ import annotations

from datetime import datetime

from lineageweave import Record, reconstruct
from lineageweave.adjudication_client import AdjudicationClientError
from lineageweave.fixtures import sample_records


def test_reconstruct_finds_the_designed_branch_point() -> None:
    """fixtures.sample_records() deliberately makes rec-002 fork into two
    threads (the revised quote, and the delivery question) -- the
    reconstruction must recover that shape without being told about it.
    """
    trees = reconstruct(sample_records())
    tree_a = next(t for t in trees if t.group_key == "A-100")

    assert "rec-001" in tree_a.roots
    assert "rec-002" in tree_a.branch_points()
    assert set(tree_a.children_of["rec-002"]) >= {"rec-003", "rec-004"}


def test_reconstruct_leaves_unrelated_records_as_their_own_root() -> None:
    """rec-006 shares no topic or project code with anything in A-100 and
    should not be force-attached to the best of a set of weak candidates.
    """
    trees = reconstruct(sample_records())
    tree_a = next(t for t in trees if t.group_key == "A-100")

    assert "rec-006" in tree_a.roots


def test_reconstruct_groups_are_independent() -> None:
    trees = reconstruct(sample_records())
    tree_b = next(t for t in trees if t.group_key == "B-200")

    assert set(tree_b.records.keys()) == {"rec-101", "rec-102", "rec-103"}
    assert "rec-101" in tree_b.roots


def test_llm_channel_is_dropped_not_faked_when_unavailable() -> None:
    trees = reconstruct(sample_records())
    tree_a = next(t for t in trees if t.group_key == "A-100")

    for edge in tree_a.edges:
        assert "llm" not in edge.channel_scores


class _StubAdjudicationClient:
    available = True

    def __init__(self) -> None:
        self.calls = 0

    def judge(self, candidate_label: str, record_label: str) -> float:
        self.calls += 1
        return 0.9 if candidate_label == record_label else 0.1


class _MalformedAdjudicationClient:
    """Available client whose provider response cannot be parsed."""

    available = True

    def judge(self, candidate_label: str, record_label: str) -> float:
        """Raise the same typed error as a malformed provider response."""

        raise AdjudicationClientError("malformed confidence")


def test_llm_channel_is_used_and_scored_when_a_client_is_supplied() -> None:
    stub = _StubAdjudicationClient()
    trees = reconstruct(sample_records(), llm=stub)
    tree_a = next(t for t in trees if t.group_key == "A-100")

    assert stub.calls > 0
    assert all("llm" in edge.channel_scores for edge in tree_a.edges)


def test_malformed_llm_confidence_degrades_one_pair_without_aborting_reconstruction() -> None:
    """Optional LLM parsing failure must not discard deterministic lineage."""
    trees = reconstruct(sample_records(), llm=_MalformedAdjudicationClient())
    tree_a = next(tree for tree in trees if tree.group_key == "A-100")

    assert tree_a.edges
    assert all(edge.channel_scores["llm"] == 0.0 for edge in tree_a.edges)


def test_candidate_window_bounds_which_priors_are_considered() -> None:
    records = [
        Record(f"r{i}", "G", f"record {i}", datetime(2026, 1, 1, i), "") for i in range(5)
    ]
    trees = reconstruct(records, candidate_window=1)
    tree = trees[0]

    for edge in tree.edges:
        parent_index = int(edge.parent_id[1:])
        child_index = int(edge.child_id[1:])
        assert child_index - parent_index == 1
