"""Demonstrates that the Knowledge Graph layer (lineageweave.knowledge_graph)
finds a real, useful relation between two posts that lineageweave.reconstruct
has no mechanism to find at all -- not just a weaker one.

Two posts about entirely different topics, in different reconstruct.py
groups (so reconstruct() never even compares them against each other --
it only fuses candidates within one group_key), still share the same
Keyman. A human reviewing "what else touches this Keyman" would want both
posts surfaced; only the KG layer can do that, because it indexes by
shared entities (people, organizations) rather than by topical/temporal
proximity within one thread.
"""

from __future__ import annotations

from datetime import datetime

from lineageweave.knowledge_graph import (
    NODE_POST,
    adjacency_from_edges,
    knowledge_graph_edges_for_post,
    node_key,
    random_walk_with_restart,
    select_related_nodes,
)
from lineageweave.models import Record
from lineageweave.reconstruct import reconstruct

_SHARED_PERSON_ID = "person-shared-keyman"


def _unrelated_posts() -> list[Record]:
    """Two posts in different groups, far apart in time, about unrelated
    topics -- exactly the shape reconstruct.py should NOT link, and by
    construction cannot: reconstruct() only ever compares records that
    share a group_key.
    """
    return [
        Record(
            "post-a",
            "group-transformers",
            "Transformer bid workshop follow-up",
            datetime(2026, 1, 1),
            "proj-transformers",
        ),
        Record(
            "post-b",
            "group-switchgear",
            "Switchgear maintenance schedule change",
            datetime(2026, 6, 1),
            "proj-switchgear",
        ),
    ]


def test_reconstruct_never_links_posts_in_different_groups() -> None:
    """Not a weak link, no probabilistic near-miss -- reconstruct.py's
    grouping means posts in different groups are structurally never
    compared, so there is categorically no edge between them, by design.
    """
    records = _unrelated_posts()
    # Each group has one record, so fusion is structurally unreachable and no
    # numeric weight is needed or invented for this boundary test.
    trees = reconstruct(records, weights={})

    tree_by_group = {tree.group_key: tree for tree in trees}
    assert set(tree_by_group) == {"group-transformers", "group-switchgear"}
    all_edges = [edge for tree in trees for edge in tree.edges]
    assert all(edge.child_id not in {"post-a", "post-b"} or edge.parent_id not in {"post-a", "post-b"} for edge in all_edges)
    # Neither post ever appears as the other's parent or child -- there is
    # no cross-group edge to even check for a specific pair here, which is
    # the point: the two records were never candidates for each other.
    linked_pairs = {(edge.parent_id, edge.child_id) for edge in all_edges}
    assert ("post-a", "post-b") not in linked_pairs
    assert ("post-b", "post-a") not in linked_pairs


def test_knowledge_graph_surfaces_the_shared_keyman_connection() -> None:
    """The same two posts, indexed by a Keyman mentioned in both -- the
    Knowledge Graph layer finds the relation reconstruct() structurally
    cannot, because it operates on a different signal (shared entities,
    not topical/temporal proximity within one thread).
    """
    edges = knowledge_graph_edges_for_post("post-a", [_SHARED_PERSON_ID])
    edges += knowledge_graph_edges_for_post("post-b", [_SHARED_PERSON_ID])

    adjacency = adjacency_from_edges(edges)
    start = node_key(NODE_POST, "post-a")
    scores = random_walk_with_restart(adjacency, start_node=start)
    related = dict(select_related_nodes(scores, start_node=start))

    assert node_key(NODE_POST, "post-b") in related
    assert related[node_key(NODE_POST, "post-b")] > 0
