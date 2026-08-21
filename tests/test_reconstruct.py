from __future__ import annotations

from datetime import UTC, datetime

from lineageweave import Record, reconstruct
from lineageweave.adjudication_client import AdjudicationUnavailableError
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
    """Each coarse source group produces an independent lineage tree."""
    trees = reconstruct(sample_records())
    tree_b = next(t for t in trees if t.group_key == "B-200")

    assert set(tree_b.records.keys()) == {"rec-101", "rec-102", "rec-103"}
    assert "rec-101" in tree_b.roots


def test_llm_channel_is_dropped_not_faked_when_unavailable() -> None:
    """The default null client leaves no fabricated LLM edge scores."""
    trees = reconstruct(sample_records())
    tree_a = next(t for t in trees if t.group_key == "A-100")

    for edge in tree_a.edges:
        assert "llm" not in edge.channel_scores


class _StubAdjudicationClient:
    """Return deterministic synthetic scores for fusion tests."""

    available = True

    def __init__(self) -> None:
        """Start with no recorded calls."""
        self.calls = 0

    def judge(self, candidate_label: str, record_label: str) -> float:
        """Score exact labels highly and other pairs weakly."""
        self.calls += 1
        return 0.9 if candidate_label == record_label else 0.1


def test_llm_channel_is_used_and_scored_when_a_client_is_supplied() -> None:
    """An available client contributes an inspectable LLM score."""
    stub = _StubAdjudicationClient()
    trees = reconstruct(sample_records(), llm=stub)
    tree_a = next(t for t in trees if t.group_key == "A-100")

    assert stub.calls > 0
    assert all("llm" in edge.channel_scores for edge in tree_a.edges)


class _InsufficientAdjudicationClient:
    """Represent an LLM channel with no evidence for any pair."""

    available = True

    def judge(self, candidate_label: str, record_label: str) -> float:
        """Report a valid per-pair evidence miss."""
        raise AdjudicationUnavailableError("synthetic evidence miss")


class _LateInsufficientAdjudicationClient:
    """Return scores before a later synthetic evidence miss."""

    available = True

    def __init__(self) -> None:
        """Start with no recorded calls."""
        self.calls = 0

    def judge(self, candidate_label: str, record_label: str) -> float:
        """Raise on the third call after two valid scores."""
        self.calls += 1
        if self.calls == 3:
            raise AdjudicationUnavailableError("synthetic later evidence miss")
        return 0.9


def test_insufficient_llm_evidence_drops_and_renormalizes_the_channel() -> None:
    """One evidence miss drops LLM instead of aborting ordinary reconstruction."""
    records = [
        Record(f"r{i}", "G", "same event", datetime(2026, 1, 1, i, tzinfo=UTC), "KEY")
        for i in range(3)
    ]
    tree = reconstruct(records, llm=_InsufficientAdjudicationClient())[0]

    assert tree.edges
    assert all("llm" not in edge.channel_scores for edge in tree.edges)


def test_late_evidence_miss_removes_prior_candidate_llm_scores() -> None:
    """A later miss removes earlier LLM scores to keep candidate weights equal."""
    client = _LateInsufficientAdjudicationClient()
    records = [
        Record(f"r{i}", "G", "same event", datetime(2026, 1, 1, i, tzinfo=UTC), "KEY")
        for i in range(3)
    ]
    tree = reconstruct(records, llm=client)[0]
    final_edge = next(edge for edge in tree.edges if edge.child_id == "r2")

    assert client.calls == 3
    assert "llm" not in final_edge.channel_scores


def test_only_missing_llm_weight_leaves_records_unattached() -> None:
    """A missing sole channel has no score to fuse and therefore creates roots."""
    records = [
        Record(f"r{i}", "G", "same event", datetime(2026, 1, 1, i, tzinfo=UTC), "KEY")
        for i in range(2)
    ]
    tree = reconstruct(
        records,
        llm=_InsufficientAdjudicationClient(),
        weights={"llm": 1.0},
    )[0]

    assert tree.edges == []
    assert set(tree.roots) == {"r0", "r1"}


def test_candidate_window_bounds_which_priors_are_considered() -> None:
    """The candidate window excludes older potential parents."""
    records = [
        Record(f"r{i}", "G", f"record {i}", datetime(2026, 1, 1, i, tzinfo=UTC), "")
        for i in range(5)
    ]
    trees = reconstruct(records, candidate_window=1)
    tree = trees[0]

    for edge in tree.edges:
        parent_index = int(edge.parent_id[1:])
        child_index = int(edge.child_id[1:])
        assert child_index - parent_index == 1
