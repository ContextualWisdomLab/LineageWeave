"""Tests for lineageweave.knowledge_graph's RWR-based relevance, against a
synthetic graph built so the correct answer is known by construction:

- hub -- spoke{1..5} (a well-connected node)
- loner -- far (an otherwise-isolated pair, disconnected from the hub
  component entirely)

If random_walk_with_restart is doing real graph math, three things must
hold: (1) directly-connected nodes outscore nodes with no path at all
(score exactly 0 for a disconnected node), (2) a well-connected node's
adaptive related-set is larger than a sparse node's using the *same*
ratio threshold -- proving the "depth" is genuinely per-node, not a fixed
constant anyone hardcoded, and (3) the algorithm is symmetric-graph-fair
(every spoke, being structurally identical, gets the same score).
"""

from __future__ import annotations

import pytest

from lineageweave.knowledge_graph import (
    EDGE_AFFILIATION,
    EDGE_CO_MENTION,
    EDGE_MENTION,
    NODE_CORPORATE_ENTITY,
    NODE_PERSON,
    NODE_POST,
    adjacency_from_edges,
    knowledge_graph_edges_for_post,
    random_walk_with_restart,
    select_related_nodes,
)


@pytest.fixture
def synthetic_graph() -> dict[str, dict[str, float]]:
    graph: dict[str, dict[str, float]] = {"hub": {}}
    for spoke in ("spoke1", "spoke2", "spoke3", "spoke4", "spoke5"):
        graph["hub"][spoke] = 1.0
        graph[spoke] = {"hub": 1.0}
    graph["loner"] = {"far": 1.0}
    graph["far"] = {"loner": 1.0}
    return graph


def test_disconnected_node_scores_exactly_zero(synthetic_graph) -> None:
    scores = random_walk_with_restart(synthetic_graph, start_node="hub")
    assert scores["loner"] == 0.0
    assert scores["far"] == 0.0


def test_symmetric_spokes_score_equally(synthetic_graph) -> None:
    scores = random_walk_with_restart(synthetic_graph, start_node="hub")
    spoke_scores = {scores[f"spoke{i}"] for i in range(1, 6)}
    assert len(spoke_scores) == 1  # every spoke got the identical score
    assert next(iter(spoke_scores)) > 0


def test_adaptive_depth_hub_reaches_more_nodes_than_a_sparse_node(synthetic_graph) -> None:
    """The core Phase 2 claim: no hop-count constant appears anywhere in
    this test or in the algorithm -- the same ratio threshold naturally
    yields a bigger related-set for the well-connected node.
    """
    hub_scores = random_walk_with_restart(synthetic_graph, start_node="hub")
    loner_scores = random_walk_with_restart(synthetic_graph, start_node="loner")

    hub_related = select_related_nodes(hub_scores, start_node="hub", min_relevance_ratio=0.05)
    loner_related = select_related_nodes(loner_scores, start_node="loner", min_relevance_ratio=0.05)

    assert len(hub_related) == 5  # all five spokes
    assert len(loner_related) == 1  # only "far" -- nothing else is reachable
    assert len(hub_related) > len(loner_related)


def test_start_node_absent_from_graph_returns_only_itself() -> None:
    scores = random_walk_with_restart({}, start_node="nowhere")
    assert scores == {"nowhere": 1.0}


def test_select_related_nodes_empty_graph_returns_empty_list() -> None:
    assert select_related_nodes({"only": 1.0}, start_node="only") == []


def test_knowledge_graph_edges_for_post_covers_mention_affiliation_and_co_mention() -> None:
    edges = knowledge_graph_edges_for_post(
        post_id="post-1",
        person_ids=["person-b", "person-a", "person-b"],
        person_corporate_entity_ids=[("person-a", "corp-1"), ("person-a", "corp-1")],
    )
    kinds = {(edge.edge_type_code, edge.source_node_id, edge.target_node_id) for edge in edges}
    assert kinds == {
        (EDGE_MENTION, "person-b", "post-1"),
        (EDGE_MENTION, "person-a", "post-1"),
        (EDGE_AFFILIATION, "person-a", "corp-1"),
        (EDGE_CO_MENTION, "person-a", "person-b"),
    }
    assert all(edge.source_node_type_code == NODE_PERSON for edge in edges)
    assert {edge.target_node_type_code for edge in edges} == {
        NODE_POST,
        NODE_CORPORATE_ENTITY,
        NODE_PERSON,
    }


def test_rwr_from_a_keyman_reaches_co_mentioned_person_and_affiliated_org() -> None:
    edges = knowledge_graph_edges_for_post(
        post_id="post-1",
        person_ids=["person-a", "person-b"],
        person_corporate_entity_ids=[("person-a", "corp-1")],
    )
    scores = random_walk_with_restart(
        adjacency_from_edges(edges), start_node=f"{NODE_PERSON}:person-a"
    )
    related = dict(
        select_related_nodes(scores, start_node=f"{NODE_PERSON}:person-a", min_relevance_ratio=0.05)
    )
    assert f"{NODE_PERSON}:person-b" in related
    assert f"{NODE_POST}:post-1" in related
    assert f"{NODE_CORPORATE_ENTITY}:corp-1" in related
    assert related[f"{NODE_PERSON}:person-b"] > 0
