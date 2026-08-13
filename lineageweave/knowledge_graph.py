"""Knowledge-graph relevance via random walk with restart (RWR).

Grounded in Tong, Faloutsos, & Pan (2006): from a starting node, RWR gives
every other node a continuous relevance score shaped by the graph's actual
connectivity, rather than a fixed hop count. That is the point of using it
here -- the product requirement is that how far a Keyman's related-nodes
view should reach differs per node (a Keyman at a hub company naturally
pulls in more than one at a two-person shell entity), and a hardcoded
`depth=2` BFS cannot express that; a relevance-score cutoff can, because it
adapts to each node's own local graph structure.

This module is pure graph math plus the typed edge-spec builder that
turns persons/affiliations/posts into ``knowledge_graph_edge`` rows.
It does not talk to Postgres. See backend/app/knowledge_graph.py for
the part that loads a Postgres subgraph into the adjacency shape this
module expects.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from itertools import combinations
from typing import Sequence

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

    Directed sinks (nodes with no positive outbound weight, including
    neighbors that appear only as targets) teleport their remaining walk
    mass back to ``start_node``. That is the standard Personalized
    PageRank treatment of a dangling column so W stays column-stochastic
    and total relevance is conserved; dropping the mass would silently
    shrink every score. Non-positive and NaN weights are ignored -- they
    are not a transition.
    """
    if start_node not in adjacency:
        return {start_node: 1.0}

    nodes = set(adjacency.keys())
    for neighbors in adjacency.values():
        nodes.update(neighbors.keys())

    outgoing: dict[str, dict[str, float]] = {}
    for node in nodes:
        outgoing[node] = {
            neighbor: weight
            for neighbor, weight in adjacency.get(node, {}).items()
            if weight > 0 and weight == weight
        }

    scores = {node: 0.0 for node in nodes}
    scores[start_node] = 1.0

    for _ in range(max_iterations):
        next_scores: dict[str, float] = defaultdict(float)
        next_scores[start_node] += restart_probability

        for node in nodes:
            neighbors = outgoing[node]
            total = sum(neighbors.values())
            walk_mass = (1 - restart_probability) * scores[node]
            if total == 0:
                next_scores[start_node] += walk_mass
                continue
            share = walk_mass / total
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


# Lookup codes written into knowledge_graph_edge / common_lookup_value.
# Prefixed so they stay unique across every lookup_category (the schema
# enforces unique(lookup_code) globally -- see migrations/0001).
NODE_PERSON = "node_person"
NODE_CORPORATE_ENTITY = "node_corporate_entity"
NODE_POST = "node_post"
EDGE_MENTION = "edge_mention"
EDGE_AFFILIATION = "edge_affiliation"
EDGE_CO_MENTION = "edge_co_mention"


@dataclass(frozen=True)
class KnowledgeGraphEdgeSpec:
    """One typed edge the application layer persists to knowledge_graph_edge.

    Node ids are opaque strings (UUIDs in the product schema). The
    polymorphic id columns have no FK -- this spec is the application-layer
    contract that a writer must have already confirmed the endpoints exist.
    """

    source_node_type_code: str
    source_node_id: str
    target_node_type_code: str
    target_node_id: str
    edge_type_code: str
    edge_weight: float = 1.0


def node_key(node_type_code: str, node_id: str) -> str:
    """Stable adjacency key: ``node_type_code:node_id``."""
    return f"{node_type_code}:{node_id}"


def parse_node_key(key: str) -> tuple[str, str]:
    """Split a ``node_key`` back into type code and id."""
    node_type_code, node_id = key.split(":", 1)
    return node_type_code, node_id


def knowledge_graph_edges_for_post(
    post_id: str,
    person_ids: Sequence[str],
    person_corporate_entity_ids: Sequence[tuple[str, str]] = (),
) -> list[KnowledgeGraphEdgeSpec]:
    """Populate the three Phase 2 edge kinds for one post.

    - person <-> post (``edge_mention``) for every mentioned person
    - person <-> corporate_entity (``edge_affiliation``) for every
      affiliation that resolved to a real ``corporate_entity`` row
    - person <-> person (``edge_co_mention``) for every unordered pair of
      people named in the same post

    Affiliation names that did not resolve to a ``corporate_entity`` are
    stored on ``person_affiliation`` but do not become graph edges -- a
    free-text org with no node id cannot be a knowledge_graph_edge
    endpoint. Directed storage is canonical (person -> post/org, and
    lexicographic person-id order for co-mentions); loaders treat the
    graph as undirected.
    """
    unique_person_ids = list(dict.fromkeys(person_ids))
    edges: list[KnowledgeGraphEdgeSpec] = []

    for person_id in unique_person_ids:
        edges.append(
            KnowledgeGraphEdgeSpec(
                source_node_type_code=NODE_PERSON,
                source_node_id=person_id,
                target_node_type_code=NODE_POST,
                target_node_id=post_id,
                edge_type_code=EDGE_MENTION,
            )
        )

    seen_affiliations: set[tuple[str, str]] = set()
    for person_id, corporate_entity_id in person_corporate_entity_ids:
        pair = (person_id, corporate_entity_id)
        if pair in seen_affiliations:
            continue
        seen_affiliations.add(pair)
        edges.append(
            KnowledgeGraphEdgeSpec(
                source_node_type_code=NODE_PERSON,
                source_node_id=person_id,
                target_node_type_code=NODE_CORPORATE_ENTITY,
                target_node_id=corporate_entity_id,
                edge_type_code=EDGE_AFFILIATION,
            )
        )

    for left, right in combinations(unique_person_ids, 2):
        source_id, target_id = (left, right) if left < right else (right, left)
        edges.append(
            KnowledgeGraphEdgeSpec(
                source_node_type_code=NODE_PERSON,
                source_node_id=source_id,
                target_node_type_code=NODE_PERSON,
                target_node_id=target_id,
                edge_type_code=EDGE_CO_MENTION,
            )
        )

    return edges


def adjacency_from_edges(edges: Sequence[KnowledgeGraphEdgeSpec]) -> Adjacency:
    """Undirected weighted adjacency for RWR, keyed as ``type:id``."""
    adjacency: Adjacency = {}
    for edge in edges:
        source = node_key(edge.source_node_type_code, edge.source_node_id)
        target = node_key(edge.target_node_type_code, edge.target_node_id)
        adjacency.setdefault(source, {})[target] = float(edge.edge_weight)
        adjacency.setdefault(target, {})[source] = float(edge.edge_weight)
    return adjacency
