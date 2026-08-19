#!/usr/bin/env python3
"""Apply the ontology-aligned buyer semantic-path repair for PR #264."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def read(path: str) -> str:
    """Read one repository text file."""
    return (ROOT / path).read_text(encoding="utf-8")


def write(path: str, content: str) -> None:
    """Write one repository text file, creating parents when needed."""
    target = ROOT / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")


def replace_once(path: str, old: str, new: str) -> None:
    """Replace one exact source anchor, accepting an already-applied patch."""
    text = read(path)
    if new in text:
        return
    if text.count(old) != 1:
        raise SystemExit(f"repair anchor mismatch in {path}: {old[:96]!r}")
    write(path, text.replace(old, new, 1))


def apply() -> None:
    """Apply the smallest complete KG → ontology → API → buyer UI repair."""
    ttl = "docs/ontology/lineageweave-kg.ttl"
    replace_once(
        ttl,
        ''':mentions a owl:ObjectProperty ;
    rdfs:domain :Post ;
    rdfs:range :Person ;
    rdfs:label "mentions" ;
    rdfs:comment "A post names a person (post_person_mention)." ;
    :lookupCode "edge_mention" .
''',
        ''':mentions a owl:ObjectProperty ;
    rdfs:domain :Person ;
    rdfs:range :Post ;
    rdfs:label "mentioned in post" ;
    rdfs:comment "Canonical knowledge_graph_edge direction for post_person_mention: the cataloged person points to the evidence post." ;
    owl:inverseOf :postMentionsPerson ;
    :lookupCode "edge_mention" .

:postMentionsPerson a owl:ObjectProperty ;
    rdfs:domain :Post ;
    rdfs:range :Person ;
    rdfs:label "mentions person" ;
    rdfs:comment "Buyer-facing inverse of :mentions: a post names a cataloged person." ;
    owl:inverseOf :mentions .
''',
    )
    for old, new in (
        (
            ''':affiliatedWith a owl:ObjectProperty ;
    rdfs:domain :Person ;
    rdfs:range :CorporateEntity ;
    rdfs:label "affiliated with" ;
    rdfs:comment "A person's N:N organizational affiliation (person_affiliation)." ;
    :lookupCode "edge_affiliation" .
''',
            ''':affiliatedWith a owl:ObjectProperty ;
    rdfs:domain :Person ;
    rdfs:range :CorporateEntity ;
    rdfs:label "affiliated with" ;
    rdfs:comment "A person's N:N organizational affiliation (person_affiliation)." ;
    owl:inverseOf :hasAffiliatedPerson ;
    :lookupCode "edge_affiliation" .

:hasAffiliatedPerson a owl:ObjectProperty ;
    rdfs:domain :CorporateEntity ;
    rdfs:range :Person ;
    rdfs:label "has affiliated person" ;
    owl:inverseOf :affiliatedWith .
''',
        ),
        (
            ''':mentionsTeam a owl:ObjectProperty ;
    rdfs:domain :Team ;
    rdfs:range :Post ;
    rdfs:label "mentioned in post" ;
    rdfs:comment "A cataloged team is named by a post (post_team_mention)." ;
    :lookupCode "edge_mention_team" .
''',
            ''':mentionsTeam a owl:ObjectProperty ;
    rdfs:domain :Team ;
    rdfs:range :Post ;
    rdfs:label "mentioned in post" ;
    rdfs:comment "A cataloged team is named by a post (post_team_mention)." ;
    owl:inverseOf :postMentionsTeam ;
    :lookupCode "edge_mention_team" .

:postMentionsTeam a owl:ObjectProperty ;
    rdfs:domain :Post ;
    rdfs:range :Team ;
    rdfs:label "mentions team" ;
    owl:inverseOf :mentionsTeam .
''',
        ),
        (
            ''':teamAffiliatedWith a owl:ObjectProperty ;
    rdfs:domain :Team ;
    rdfs:range :CorporateEntity ;
    rdfs:label "team affiliated with" ;
    rdfs:comment "The company a cataloged team belongs to (cataloged_team.affiliated_corporate_entity_id)." ;
    :lookupCode "edge_team_affiliation" .
''',
            ''':teamAffiliatedWith a owl:ObjectProperty ;
    rdfs:domain :Team ;
    rdfs:range :CorporateEntity ;
    rdfs:label "team affiliated with" ;
    rdfs:comment "The company a cataloged team belongs to (cataloged_team.affiliated_corporate_entity_id)." ;
    owl:inverseOf :hasAffiliatedTeam ;
    :lookupCode "edge_team_affiliation" .

:hasAffiliatedTeam a owl:ObjectProperty ;
    rdfs:domain :CorporateEntity ;
    rdfs:range :Team ;
    rdfs:label "has affiliated team" ;
    owl:inverseOf :teamAffiliatedWith .
''',
        ),
        (
            ''':mentionsOrganization a owl:ObjectProperty ;
    rdfs:domain :CorporateEntity ;
    rdfs:range :Post ;
    rdfs:label "mentioned in post" ;
    rdfs:comment "A resolved organization is named by a post (post_organization_mention)." ;
    :lookupCode "edge_mention_organization" .
''',
            ''':mentionsOrganization a owl:ObjectProperty ;
    rdfs:domain :CorporateEntity ;
    rdfs:range :Post ;
    rdfs:label "mentioned in post" ;
    rdfs:comment "A resolved organization is named by a post (post_organization_mention)." ;
    owl:inverseOf :postMentionsOrganization ;
    :lookupCode "edge_mention_organization" .

:postMentionsOrganization a owl:ObjectProperty ;
    rdfs:domain :Post ;
    rdfs:range :CorporateEntity ;
    rdfs:label "mentions organization" ;
    owl:inverseOf :mentionsOrganization .
''',
        ),
    ):
        replace_once(ttl, old, new)

    ontology = "lineageweave/ontology.py"
    replace_once(
        ontology,
        "def all_declared_lookup_codes() -> set[str]:\n",
        '''def relationship_annotations(lookup_code: str, *, reverse: bool = False) -> dict[str, str]:
    """Return the OWL relationship IRI and buyer-facing label for a traversal."""
    subject = _term_subject(lookup_code)
    if subject is None:
        return {}
    relationship = subject
    if reverse and (subject, RDF.type, OWL.SymmetricProperty) not in ONTOLOGY:
        relationship = ONTOLOGY.value(subject, OWL.inverseOf)
        if relationship is None:
            relationship = next(ONTOLOGY.subjects(OWL.inverseOf, subject), None)
        if relationship is None:
            relationship = subject
    fields = {"relationship_iri": str(relationship)}
    label = ONTOLOGY.value(relationship, RDFS.label)
    if label is not None:
        fields["relationship_label"] = str(label)
    return fields


def all_declared_lookup_codes() -> set[str]:
''',
    )
    replace_once(
        ontology,
        '    "ontology_annotations",\n]',
        '    "ontology_annotations",\n    "relationship_annotations",\n]',
    )

    graph = "lineageweave/knowledge_graph.py"
    replace_once(graph, "from collections import defaultdict\n", "from collections import defaultdict, deque\n")
    replace_once(graph, "from typing import Sequence\n", "from typing import Literal, Sequence\n")
    replace_once(
        graph,
        "def node_key(node_type_code: str, node_id: str) -> str:\n",
        '''@dataclass(frozen=True)
class KnowledgeGraphPathHop:
    """One ontology-bearing traversal step through a stored KG edge."""

    from_node_type_code: str
    from_node_id: str
    edge_type_code: str
    to_node_type_code: str
    to_node_id: str
    traversal_direction: Literal["forward", "reverse"]
    edge_weight: float = 1.0


def node_key(node_type_code: str, node_id: str) -> str:
''',
    )
    replace_once(
        graph,
        "def adjacency_from_edges(edges: Sequence[KnowledgeGraphEdgeSpec]) -> Adjacency:\n",
        '''def semantic_paths_from_edges(
    edges: Sequence[KnowledgeGraphEdgeSpec],
    start_node: str,
) -> dict[str, tuple[KnowledgeGraphPathHop, ...]]:
    """Return deterministic shortest relationship paths over positive stored edges."""
    incident: dict[str, list[tuple[str, KnowledgeGraphPathHop]]] = defaultdict(list)
    for edge in edges:
        weight = float(edge.edge_weight)
        if not (weight > 0 and weight == weight):
            continue
        source = node_key(edge.source_node_type_code, edge.source_node_id)
        target = node_key(edge.target_node_type_code, edge.target_node_id)
        incident[source].append((target, KnowledgeGraphPathHop(
            edge.source_node_type_code, edge.source_node_id, edge.edge_type_code,
            edge.target_node_type_code, edge.target_node_id, "forward", weight,
        )))
        incident[target].append((source, KnowledgeGraphPathHop(
            edge.target_node_type_code, edge.target_node_id, edge.edge_type_code,
            edge.source_node_type_code, edge.source_node_id, "reverse", weight,
        )))
    for hops in incident.values():
        hops.sort(key=lambda item: (-item[1].edge_weight, item[1].edge_type_code,
                                    item[1].to_node_type_code, item[1].to_node_id,
                                    item[1].traversal_direction))
    paths: dict[str, tuple[KnowledgeGraphPathHop, ...]] = {start_node: ()}
    pending: deque[str] = deque([start_node])
    while pending:
        current = pending.popleft()
        for neighbor, hop in incident.get(current, []):
            if neighbor in paths:
                continue
            paths[neighbor] = (*paths[current], hop)
            pending.append(neighbor)
    return paths


def adjacency_from_edges(edges: Sequence[KnowledgeGraphEdgeSpec]) -> Adjacency:
''',
    )

    backend = "backend/app/knowledge_graph.py"
    replace_once(
        backend,
        "from lineageweave.ontology import ontology_annotations\n",
        "from lineageweave.ontology import ontology_annotations, relationship_annotations\n",
    )
    replace_once(
        backend,
        "    select_related_nodes,\n)",
        "    select_related_nodes,\n    semantic_paths_from_edges,\n)",
    )
    replace_once(
        backend,
        '''    scores = random_walk_with_restart(adjacency_from_edges(edges), start_node=start)
    related = select_related_nodes(scores, start_node=start)
    return await hydrate_related_nodes(conn, related)
''',
        '''    scores = random_walk_with_restart(adjacency_from_edges(edges), start_node=start)
    related = select_related_nodes(scores, start_node=start)
    semantic_paths = semantic_paths_from_edges(edges, start)
    payload = await hydrate_related_nodes(conn, related)
    for item in payload:
        related_key = node_key(item["node_type_code"], item["node_id"])
        item["semantic_path"] = [
            {
                "from_node_type_code": hop.from_node_type_code,
                "to_node_type_code": hop.to_node_type_code,
                "edge_type_code": hop.edge_type_code,
                "traversal_direction": hop.traversal_direction,
                **relationship_annotations(
                    hop.edge_type_code,
                    reverse=hop.traversal_direction == "reverse",
                ),
            }
            for hop in semantic_paths.get(related_key, ())
        ]
    return payload
''',
    )

    api = "frontend/src/api.ts"
    replace_once(
        api,
        '''export interface RelatedNode {
  node_id: string;
  node_type_code: RelatedNodeType | string;
  relevance: number;
  label?: string;
  post_body_excerpt?: string | null;
  post_body_truncated?: boolean;
  person_side_code?: string;
  person_side_label?: string;
  ontology_iri?: string;
  ontology_label?: string;
}
''',
        '''export interface SemanticPathHop {
  from_node_type_code: RelatedNodeType | string;
  to_node_type_code: RelatedNodeType | string;
  edge_type_code: string;
  traversal_direction: "forward" | "reverse";
  relationship_iri?: string;
  relationship_label?: string;
}

export interface RelatedNode {
  node_id: string;
  node_type_code: RelatedNodeType | string;
  relevance: number;
  label?: string;
  post_body_excerpt?: string | null;
  post_body_truncated?: boolean;
  person_side_code?: string;
  person_side_label?: string;
  ontology_iri?: string;
  ontology_label?: string;
  semantic_path?: SemanticPathHop[];
}
''',
    )
    write(
        "frontend/src/components/RelatedSemanticPath.tsx",
        '''import type { SemanticPathHop } from "../api";
import { t } from "../i18n";

export function semanticPathText(semanticPath?: SemanticPathHop[]): string {
  const labels = (semanticPath ?? [])
    .map((hop) => hop.relationship_label ?? hop.edge_type_code)
    .filter((label) => label.length > 0);
  return labels.length > 0 ? labels.join(" → ") : t("Graph relation");
}

export function RelatedSemanticPath({ semanticPath }: { semanticPath?: SemanticPathHop[] }) {
  const text = semanticPathText(semanticPath);
  return <span className="related-post-kind" title={text}>{text}</span>;
}
''',
    )
    replace_once(
        "frontend/src/App.tsx",
        'import { PopupCloseButton } from "./components/PopupCloseButton";\n',
        'import { PopupCloseButton } from "./components/PopupCloseButton";\nimport { RelatedSemanticPath } from "./components/RelatedSemanticPath";\n',
    )
    replace_once(
        "frontend/src/App.tsx",
        '<span className="related-post-kind">{t("Graph relation")}</span>',
        '<RelatedSemanticPath semanticPath={node.semantic_path} />',
    )

    replace_once(
        "tests/test_ontology.py",
        "from rdflib.namespace import RDFS, SKOS\n",
        "from rdflib.namespace import OWL, RDFS, SKOS\n",
    )
    replace_once(
        "tests/test_ontology.py",
        '''def test_mentions_property_domain_and_range_match_the_schema() -> None:
    """`mentions` goes Post -> Person, matching post_person_mention's
    actual foreign keys -- not just any two classes."""
    graph = load_ontology()
    assert (LW.mentions, RDFS.domain, LW.Post) in graph
    assert (LW.mentions, RDFS.range, LW.Person) in graph
''',
        '''def test_mentions_property_domain_and_range_match_canonical_edge_direction() -> None:
    """``edge_mention`` is stored Person -> Post; OWL and its inverse agree."""
    graph = load_ontology()
    assert (LW.mentions, RDFS.domain, LW.Person) in graph
    assert (LW.mentions, RDFS.range, LW.Post) in graph
    assert (LW.mentions, OWL.inverseOf, LW.postMentionsPerson) in graph
    assert (LW.postMentionsPerson, RDFS.domain, LW.Post) in graph
    assert (LW.postMentionsPerson, RDFS.range, LW.Person) in graph
''',
    )

    write(
        "tests/test_semantic_relationship_paths.py",
        '''"""Regressions for ontology-aligned buyer-visible KG relationship paths."""

from rdflib.namespace import OWL, RDFS

from lineageweave.knowledge_graph import (
    EDGE_AFFILIATION,
    EDGE_CO_MENTION,
    EDGE_MENTION,
    NODE_CORPORATE_ENTITY,
    NODE_PERSON,
    NODE_POST,
    KnowledgeGraphEdgeSpec,
    node_key,
    semantic_paths_from_edges,
)
from lineageweave.ontology import LW, load_ontology, relationship_annotations


def test_person_mention_ontology_matches_canonical_edge_direction() -> None:
    graph = load_ontology()
    assert (LW.mentions, RDFS.domain, LW.Person) in graph
    assert (LW.mentions, RDFS.range, LW.Post) in graph
    assert (LW.mentions, OWL.inverseOf, LW.postMentionsPerson) in graph


def test_relationship_annotations_use_inverse_buyer_label() -> None:
    assert relationship_annotations(EDGE_MENTION)["relationship_label"] == "mentioned in post"
    assert relationship_annotations(EDGE_MENTION, reverse=True)["relationship_label"] == "mentions person"
    assert relationship_annotations(EDGE_CO_MENTION, reverse=True)["relationship_label"] == "co-mentioned with"
    assert relationship_annotations("not_a_real_lookup_code") == {}


def test_semantic_paths_are_shortest_directional_and_deterministic() -> None:
    edges = [
        KnowledgeGraphEdgeSpec(NODE_PERSON, "person-a", NODE_POST, "post-1", EDGE_MENTION),
        KnowledgeGraphEdgeSpec(NODE_PERSON, "person-b", NODE_POST, "post-1", EDGE_MENTION),
        KnowledgeGraphEdgeSpec(NODE_PERSON, "person-a", NODE_CORPORATE_ENTITY, "corp-1", EDGE_AFFILIATION),
    ]
    paths = semantic_paths_from_edges(list(reversed(edges)), node_key(NODE_PERSON, "person-a"))
    assert [(hop.edge_type_code, hop.traversal_direction) for hop in paths[node_key(NODE_POST, "post-1")]] == [(EDGE_MENTION, "forward")]
    assert [(hop.edge_type_code, hop.traversal_direction) for hop in paths[node_key(NODE_PERSON, "person-b")]] == [(EDGE_MENTION, "forward"), (EDGE_MENTION, "reverse")]
''',
    )
    write(
        "frontend/src/components/RelatedSemanticPath.test.tsx",
        '''import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { RelatedSemanticPath, semanticPathText } from "./RelatedSemanticPath";

describe("RelatedSemanticPath", () => {
  it("renders the ontology relationship path instead of generic graph copy", () => {
    render(<RelatedSemanticPath semanticPath={[{
      from_node_type_code: "node_person",
      to_node_type_code: "node_post",
      edge_type_code: "edge_mention",
      traversal_direction: "forward",
      relationship_iri: "https://contextualwisdomlab.github.io/lineageweave/ontology#mentions",
      relationship_label: "mentioned in post",
    }]} />);
    expect(screen.getByText("mentioned in post")).toBeInTheDocument();
    expect(semanticPathText(undefined)).toBe("Graph relation");
  });
});
''',
    )
    write(
        "docs/adr/0090-ontology-grounded-semantic-relationship-path.md",
        '''# ADR 0090: Ontology-grounded semantic relationship paths

## Status

Accepted

## Context

The buyer related-node surface ranked evidence-gated knowledge-graph nodes with RWR but discarded relationship predicates. It could only show a node class, relevance score, and generic `Graph relation` copy. The ontology also declared `edge_mention` as `Post -> Person` while the canonical `knowledge_graph_edge` projection stores `Person -> Post`.

## Decision

- Keep canonical relational edge direction.
- Align OWL domain/range with storage and declare explicit `owl:inverseOf` terms for reverse buyer traversal.
- Use RWR only for relevance selection; explain each selected node with a deterministic shortest path over the same positive evidence-gated subgraph.
- Return per-hop edge code, traversal direction, ontology IRI, and label. Missing ontology terms stay missing.
- Render the semantic path in the buyer related-node surface. The path explains stored connectivity and is not a causal claim.

## Consequences

The API extension is additive. PostgreSQL remains the system of record. Buyer surfaces now preserve relationship semantics instead of collapsing them to a numeric relevance score.
''',
    )
    write(
        "docs/doctoring/SEMANTIC_RELATIONSHIP_PATH_REFERENCES.md",
        '''# Semantic relationship path references

## Product traceability

`knowledge_graph_edge` direction, OWL domain/range, inverse traversal labels, and buyer-visible semantic paths must agree. `knowledge_graph_edge_evidence` remains the authorization/evidence gate; semantic paths do not create facts.

## APA 7th references

World Wide Web Consortium. (2012). *OWL 2 Web Ontology Language: Document overview (Second Edition).* https://www.w3.org/TR/owl2-overview/

World Wide Web Consortium. (2013). *PROV-O: The PROV ontology.* https://www.w3.org/TR/prov-o/
''',
    )
    write(
        "CHANGELOG.d/2.17.0-ontology-semantic-path.md",
        '''### Fixed

- Aligned `edge_mention` OWL semantics with the canonical Person-to-Post graph direction and added explicit inverse relationship terms.
- Buyer related nodes now carry and render ontology-grounded relationship paths instead of generic graph copy.
''',
    )


if __name__ == "__main__":
    apply()
