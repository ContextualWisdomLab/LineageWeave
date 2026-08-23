from __future__ import annotations

import difflib
from datetime import datetime

from lineageweave import Record, reconstruct
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


def test_llm_channel_is_used_and_scored_when_a_client_is_supplied() -> None:
    stub = _StubAdjudicationClient()
    trees = reconstruct(sample_records(), llm=stub)
    tree_a = next(t for t in trees if t.group_key == "A-100")

    assert stub.calls > 0
    assert all("llm" in edge.channel_scores for edge in tree_a.edges)


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


class _StubEmbeddingClient:
    """Maps each known label to a fixed vector so a test controls cosine
    similarity directly, instead of depending on a real provider's opinion."""

    available = True

    def __init__(self, vectors_by_label: dict[str, list[float]]) -> None:
        self._vectors_by_label = vectors_by_label
        self.calls = 0

    def embed(self, text: str) -> list[float]:
        self.calls += 1
        return self._vectors_by_label[text]


def test_embedding_channel_is_used_and_scored_when_a_client_is_supplied() -> None:
    stub = _StubEmbeddingClient({record.label: [1.0, 0.0] for record in sample_records()})
    trees = reconstruct(sample_records(), embedding=stub)
    tree_a = next(t for t in trees if t.group_key == "A-100")

    assert stub.calls > 0
    assert all("text" in edge.channel_scores for edge in tree_a.edges)
    # Every label maps to the identical vector here, so cosine similarity is
    # exactly 1.0 for every pair -- distinct from whatever difflib would
    # have scored the same real (non-identical) titles.
    assert all(edge.channel_scores["text"] == 1.0 for edge in tree_a.edges)


def test_embedding_channel_overrides_a_difflib_false_positive() -> None:
    """Reproduces the reported production bug: two posts about different
    topics ('budget' vs 'safety') share enough words and structure that
    difflib.SequenceMatcher alone scores them a 0.86 character-overlap
    ratio -- high enough, combined with temporal closeness, to clear
    DEFAULT_MIN_FUSED_SCORE and force a spurious parent-child Event Lineage
    edge between unrelated posts (see docs/product-technical-gap-baseline.md).

    The stub vectors below give a raw cosine of 0.05 -- a low, but not
    artificially perfect, positive similarity -- rather than exactly
    opposite (-1.0) unit vectors. Real sentence embeddings occupy an
    anisotropic cone (Ethayarajh, 2019): two genuinely unrelated texts from
    an actual provider essentially never score near -1, so a fixture that
    only proves the fix works at that unrealistic extreme would not have
    caught the (cosine+1)/2 remap bug this test also guards against (see
    lineageweave/embedding_client.py::cosine_similarity) -- that remap would
    have turned even a true -1.0 into 0.0, same as this clamp does, but it
    would *also* have turned this test's realistic 0.05 into a
    floor-clearing ~0.525. Clamping instead of remapping is what keeps this
    pair apart.
    """
    budget_label = "Quarterly budget review for the northern region team"
    safety_label = "Quarterly safety review for the northern region plant"
    records = [
        Record("r1", "G", budget_label, datetime(2026, 1, 1, 0, 0), ""),
        Record("r2", "G", safety_label, datetime(2026, 1, 1, 1, 0), ""),
    ]

    assert difflib.SequenceMatcher(None, budget_label, safety_label).ratio() > 0.8

    without_embedding = reconstruct(records)
    assert without_embedding[0].edges, (
        "sanity check: difflib's character overlap alone should reproduce "
        "the false-positive link this test's embedding channel must prevent"
    )

    low_similarity_vector = [0.05, 0.9987492177719986]  # cosine 0.05 against [1.0, 0.0]
    stub = _StubEmbeddingClient({budget_label: [1.0, 0.0], safety_label: low_similarity_vector})
    with_embedding = reconstruct(records, embedding=stub)
    assert with_embedding[0].edges == []
    assert "r2" in with_embedding[0].roots


def test_embedding_channel_is_dropped_not_faked_when_unavailable() -> None:
    trees = reconstruct(sample_records())
    tree_a = next(t for t in trees if t.group_key == "A-100")

    # No embedding client was supplied, so every "text" score must have come
    # from text_similarity_score's difflib stand-in, never a fabricated
    # cosine similarity -- there is nothing to assert this *against* beyond
    # the channel simply working exactly as it did before this client existed.
    assert all("text" in edge.channel_scores for edge in tree_a.edges)
