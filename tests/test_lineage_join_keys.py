"""Join keys label reconstruct edges. Missing ontology objects fail-close that branch."""

from lineageweave.lineage_join_keys import (
    JOIN_KEYMAN,
    JOIN_ONTOLOGY_OBJECT,
    JOIN_WIN_POOL,
    ONTOLOGY_OBJECT_EMPTY_NEXT_ACTION,
    PostJoinFacts,
    annotate_lineage_edges,
    join_keys_for_pair,
    ontology_object_is_declared,
)


def test_same_keyman_and_win_pool_label_the_edge() -> None:
    left = PostJoinFacts("post-1", "A-100", frozenset({"person-ada"}), frozenset({"corp-1"}), frozenset())
    right = PostJoinFacts("post-2", "A-100", frozenset({"person-ada"}), frozenset({"corp-1"}), frozenset())
    keys = join_keys_for_pair(left, right)
    assert keys.codes == (JOIN_KEYMAN, JOIN_WIN_POOL, JOIN_ONTOLOGY_OBJECT)
    assert "같은 Keyman" in keys.labels
    assert "같은 수주풀" in keys.labels
    assert keys.empty_next_action is None


def test_unbound_object_fail_closes_that_branch_only() -> None:
    left = PostJoinFacts("post-1", "A-100", frozenset(), frozenset(), frozenset({"Uncataloged Widget"}))
    right = PostJoinFacts("post-2", "A-100", frozenset(), frozenset(), frozenset({"Uncataloged Widget"}))
    keys = join_keys_for_pair(left, right)
    assert JOIN_ONTOLOGY_OBJECT not in keys.codes
    assert keys.empty_next_action == ONTOLOGY_OBJECT_EMPTY_NEXT_ACTION


def test_annotate_does_not_invent_a_searxng_parent() -> None:
    facts = {
        "post-1": PostJoinFacts("post-1", "A-100", frozenset({"person-ada"}), frozenset(), frozenset()),
        "post-2": PostJoinFacts("post-2", "A-100", frozenset({"person-ada"}), frozenset(), frozenset()),
    }
    edges = annotate_lineage_edges(
        [{"source": "post-1", "target": "post-2", "fused_score": 0.8}],
        facts,
    )
    assert len(edges) == 1
    assert edges[0]["join_keys"][0]["label"] == "같은 Keyman"
    assert all(edge["source"] in {"post-1", "post-2"} for edge in edges)


def test_undeclared_lookup_is_not_an_ontology_object() -> None:
    assert ontology_object_is_declared("node_corporate_entity")
    assert not ontology_object_is_declared("not-a-real-lookup")
