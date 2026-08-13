"""Knowledge-graph relevance via random walk with restart (RWR).

Grounded in Tong, Faloutsos, & Pan (2006): from a starting node, RWR gives
every other node a continuous relevance score shaped by the graph's actual
connectivity, rather than a fixed hop count. That is the point of using it
here -- the product requirement is that how far a Keyman's related-nodes
view should reach differs per node (a Keyman at a hub company naturally
pulls in more than one at a two-person shell entity), and a hardcoded
`depth=2` BFS cannot express that; a relevance-score cutoff can, because it
adapts to each node's own local graph structure.

This module is pure graph math -- no Postgres, no knowledge_graph_edge
schema awareness. See backend/app/knowledge_graph.py for the part that
loads a Postgres subgraph into the adjacency shape this module expects.
"""

from __future__ import annotations

from collections import defaultdict

Adjacency = dict[str, dict[str, float]]

DEFAULT_RESTART_PROBABILITY = 0.15
DEFAULT_MAX_ITERATIONS = 100
DEFAULT_TOLERANCE = 1e-6


def random_walk_with_restart(
    adjacency: Adjacency,
    start_node: str,
    restart_probability: float = DEFAULT_RESTART_PROBABILITY,
    max_iterations: int = DEFAULT_MAX_ITERATIONS,
    tolerance: float = DEFAULT_TOLERANCE,
) -> dict[str, float]:
    """Steady-state RWR relevance scores from `start_node` to every node
    reachable in `adjacency` (an undirected or directed weighted graph,
    given as node -> {neighbor: edge_weight}).

    Power iteration on r = c*e_q + (1-c)*W^T r (Tong et al., 2006, eq. 2),
    where c is the restart probability, e_q is the one-hot start vector,
    and W is the column-normalized transition matrix. Converges quickly
    for the small (single-post-scoped) subgraphs this is used against;
    a closed-form solve isn't worth the added complexity at that scale.
    """
    if start_node not in adjacency:
        return {start_node: 1.0}

    nodes = set(adjacency.keys())
    for neighbors in adjacency.values():
        nodes.update(neighbors.keys())

    out_weight_totals = {node: sum(adjacency.get(node, {}).values()) for node in nodes}

    scores = {node: 0.0 for node in nodes}
    scores[start_node] = 1.0

    for _ in range(max_iterations):
        next_scores: dict[str, float] = defaultdict(float)
        next_scores[start_node] += restart_probability

        for node, neighbors in adjacency.items():
            total = out_weight_totals[node]
            if total == 0:
                continue
            share = (1 - restart_probability) * scores[node] / total
            for neighbor, weight in neighbors.items():
                next_scores[neighbor] += share * weight

        delta = sum(abs(next_scores[node] - scores[node]) for node in nodes)
        scores = {node: next_scores.get(node, 0.0) for node in nodes}
        if delta < tolerance:
            break

    return scores


def select_related_nodes(
    scores: dict[str, float],
    start_node: str,
    min_relevance_ratio: float = 0.05,
    max_nodes: int = 20,
) -> list[tuple[str, float]]:
    """Per-node adaptive cutoff: keep any node whose score is at least
    `min_relevance_ratio` of the *top* non-start score, capped at
    `max_nodes`. Two different start nodes naturally yield different
    effective reach with the same ratio -- a hub's related set extends
    further than a sparsely-connected node's, which is the whole point of
    using RWR instead of a fixed hop count.
    """
    candidates = sorted(
        ((node, score) for node, score in scores.items() if node != start_node),
        key=lambda item: item[1],
        reverse=True,
    )
    if not candidates:
        return []
    top_score = candidates[0][1]
    if top_score <= 0:
        return []
    threshold = top_score * min_relevance_ratio
    return [(node, score) for node, score in candidates if score >= threshold][:max_nodes]
