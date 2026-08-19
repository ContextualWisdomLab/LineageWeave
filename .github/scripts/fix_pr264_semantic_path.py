#!/usr/bin/env python3
"""Apply the test-first PR 264 ontology relationship-path repair."""

from __future__ import annotations

import argparse
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ONTOLOGY = ROOT / "docs" / "ontology" / "lineageweave-kg.ttl"
ONTOLOGY_MODULE = ROOT / "lineageweave" / "ontology.py"
GRAPH_MODULE = ROOT / "lineageweave" / "knowledge_graph.py"
BACKEND_GRAPH = ROOT / "backend" / "app" / "knowledge_graph.py"
API_TYPES = ROOT / "frontend" / "src" / "api.ts"
APP = ROOT / "frontend" / "src" / "App.tsx"
ONTOLOGY_TEST = ROOT / "tests" / "test_ontology.py"
PROJECTION_TEST = ROOT / "tests" / "test_person_mention_projection.py"
PYTHON_RED = ROOT / "tests" / "test_semantic_relationship_paths.py"
FRONTEND_COMPONENT = ROOT / "frontend" / "src" / "components" / "RelatedSemanticPath.tsx"
FRONTEND_RED = ROOT / "frontend" / "src" / "components" / "RelatedSemanticPath.test.tsx"
DOCTORING = ROOT / "docs" / "doctoring" / "SEMANTIC_RELATIONSHIP_PATH_REFERENCES.md"
CHANGELOG = ROOT / "CHANGELOG.d" / "2.17.0-ontology-semantic-path.md"


def read(path: Path) -> str:
    """Read one UTF-8 repository file."""

    return path.read_text(encoding="utf-8")


def write(path: Path, content: str) -> None:
    """Write one UTF-8 repository file, creating its parent directory."""

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def replace_once(path: Path, old: str, new: str, label: str) -> None:
    """Replace exactly one anchor, while remaining idempotent after success."""

    text = read(path)
    if new in text:
        return
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{label}: expected one anchor in {path}, got {count}")
    write(path, text.replace(old, new, 1))


def write_red() -> None:
    """Write regressions that fail before the production semantic contract exists."""

    write(
        PYTHON_RED,
        '''"""Regressions for ontology-aligned, buyer-visible KG relationship paths."""

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
    """The relational edge is Person -> Post, so OWL must say the same."""

    graph = load_ontology()
    assert (LW.mentions, RDFS.domain, LW.Person) in graph
    assert (LW.mentions, RDFS.range, LW.Post) in graph
    assert (LW.mentions, OWL.inverseOf, LW.postMentionsPerson) in graph
    assert (LW.postMentionsPerson, RDFS.domain, LW.Post) in graph
    assert (LW.postMentionsPerson, RDFS.range, LW.Person) in graph


def test_relationship_annotations_select_the_inverse_buyer_label() -> None:
    """Reverse traversal must expose the inverse property, not a false direction."""

    assert relationship_annotations(EDGE_MENTION) == {
        "relationship_iri": str(LW.mentions),
        "relationship_label": "mentioned in post",
    }
    assert relationship_annotations(EDGE_MENTION, reverse=True) == {
        "relationship_iri": str(LW.postMentionsPerson),
        "relationship_label": "mentions person",
    }
    assert relationship_annotations(EDGE_CO_MENTION, reverse=True) == {
        "relationship_iri": str(LW.coMentionedWith),
        "relationship_label": "co-mentioned with",
    }
    assert relationship_annotations("not_a_real_lookup_code") == {}


def test_semantic_paths_are_shortest_directional_and_deterministic() -> None:
    """A path explains the stored graph without depending on edge input order."""

    edges = [
        KnowledgeGraphEdgeSpec(
            NODE_PERSON,
            "person-a",
            NODE_POST,
            "post-1",
            EDGE_MENTION,
        ),
        KnowledgeGraphEdgeSpec(
            NODE_PERSON,
            "person-b",
            NODE_POST,
            "post-1",
            EDGE_MENTION,
        ),
        KnowledgeGraphEdgeSpec(
            NODE_PERSON,
            "person-a",
            NODE_CORPORATE_ENTITY,
            "corp-1",
            EDGE_AFFILIATION,
        ),
    ]
    start = node_key(NODE_PERSON, "person-a")
    paths = semantic_paths_from_edges(list(reversed(edges)), start)

    post_path = paths[node_key(NODE_POST, "post-1")]
    assert [
        (
            hop.from_node_id,
            hop.edge_type_code,
            hop.to_node_id,
            hop.traversal_direction,
        )
        for hop in post_path
    ] == [("person-a", EDGE_MENTION, "post-1", "forward")]

    other_person_path = paths[node_key(NODE_PERSON, "person-b")]
    assert [
        (
            hop.from_node_id,
            hop.edge_type_code,
            hop.to_node_id,
            hop.traversal_direction,
        )
        for hop in other_person_path
    ] == [
        ("person-a", EDGE_MENTION, "post-1", "forward"),
        ("post-1", EDGE_MENTION, "person-b", "reverse"),
    ]
    assert paths[node_key(NODE_CORPORATE_ENTITY, "corp-1")][0].edge_type_code == EDGE_AFFILIATION
''',
    )
    write(
        FRONTEND_RED,
        '''import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it } from "vitest";
import { setLocale } from "../i18n";
import { RelatedSemanticPath, semanticPathText } from "./RelatedSemanticPath";

const semanticPath = [
  {
    from_node_type_code: "node_person",
    from_node_id: "person-a",
    to_node_type_code: "node_post",
    to_node_id: "post-1",
    edge_type_code: "edge_mention",
    traversal_direction: "forward" as const,
    relationship_iri: "https://contextualwisdomlab.github.io/lineageweave/ontology#mentions",
    relationship_label: "mentioned in post",
  },
  {
    from_node_type_code: "node_post",
    from_node_id: "post-1",
    to_node_type_code: "node_person",
    to_node_id: "person-b",
    edge_type_code: "edge_mention",
    traversal_direction: "reverse" as const,
    relationship_iri: "https://contextualwisdomlab.github.io/lineageweave/ontology#postMentionsPerson",
    relationship_label: "mentions person",
  },
];

describe("RelatedSemanticPath", () => {
  beforeEach(() => setLocale("en"));

  it("renders the ontology relationship path instead of generic graph copy", () => {
    render(<RelatedSemanticPath semanticPath={semanticPath} />);
    expect(screen.getByText("mentioned in post → mentions person")).toBeInTheDocument();
    expect(semanticPathText(undefined)).toBe("Graph relation");
  });
});
''',
    )


def next_adr_path() -> Path:
    """Choose the next ADR number across this branch and the live stack parent."""

    names = [path.name for path in (ROOT / "docs" / "adr").glob("[0-9][0-9][0-9][0-9]-*.md")]
    try:
        result = subprocess.run(
            [
                "git",
                "ls-tree",
                "-r",
                "--name-only",
                "origin/feat/analysis-run-name-evidence-lineage",
                "docs/adr",
            ],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        )
        names.extend(Path(line).name for line in result.stdout.splitlines())
    except subprocess.CalledProcessError:
        pass
    numbers = [
        int(match.group(1))
        for name in names
        if (match := re.match(r"^(\d{4})-", name)) is not None
    ]
    number = max(numbers, default=0) + 1
    return ROOT / "docs" / "adr" / f"{number:04d}-ontology-grounded-semantic-relationship-path.md"


def apply() -> None:
    """Apply the narrow ontology, API, and buyer-surface implementation."""

    replace_once(
        ONTOLOGY,
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
        "person mention ontology direction",
    )
    replace_once(
        ONTOLOGY,
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
        "person affiliation inverse",
    )
    replace_once(
        ONTOLOGY,
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
        "team mention inverse",
    )
    replace_once(
        ONTOLOGY,
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
        "team affiliation inverse",
    )
    replace_once(
        ONTOLOGY,
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
        "organization mention inverse",
    )

    replace_once(
        ONTOLOGY_MODULE,
        "def all_declared_lookup_codes() -> set[str]:\n",
        '''def relationship_annotations(lookup_code: str, *, reverse: bool = False) -> dict[str, str]:
    """Return the ontology predicate IRI and direction-correct label.

    ``knowledge_graph_edge`` stores one canonical direction. Reverse graph
    traversal selects the declared ``owl:inverseOf`` property. Symmetric
    properties retain their own term. Missing terms stay missing rather than
    receiving guessed semantics.
    """

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
        "relationship ontology annotations",
    )
    replace_once(
        ONTOLOGY_MODULE,
        '    "ontology_annotations",\n]\n',
        '    "ontology_annotations",\n    "relationship_annotations",\n]\n',
        "ontology module export",
    )

    replace_once(
        GRAPH_MODULE,
        "from collections import defaultdict\n",
        "from collections import defaultdict, deque\n",
        "semantic path deque import",
    )
    replace_once(
        GRAPH_MODULE,
        "from typing import Sequence\n",
        "from typing import Literal, Sequence\n",
        "semantic path type import",
    )
    replace_once(
        GRAPH_MODULE,
        "def node_key(node_type_code: str, node_id: str) -> str:\n",
        '''@dataclass(frozen=True)
class KnowledgeGraphPathHop:
    """One direction-aware traversal step through a stored KG assertion."""

    from_node_type_code: str
    from_node_id: str
    edge_type_code: str
    to_node_type_code: str
    to_node_id: str
    traversal_direction: Literal["forward", "reverse"]
    edge_weight: float = 1.0


def node_key(node_type_code: str, node_id: str) -> str:
''',
        "semantic path hop contract",
    )
    replace_once(
        GRAPH_MODULE,
        "def adjacency_from_edges(edges: Sequence[KnowledgeGraphEdgeSpec]) -> Adjacency:\n",
        '''def semantic_paths_from_edges(
    edges: Sequence[KnowledgeGraphEdgeSpec],
    start_node: str,
) -> dict[str, tuple[KnowledgeGraphPathHop, ...]]:
    """Return deterministic shortest relationship paths from ``start_node``.

    RWR determines which nodes are relevant. This breadth-first projection
    explains why each reachable node is connected using the same positive,
    evidence-gated edges. Ties prefer higher edge weight, then stable typed
    identifiers. The path describes stored connectivity and is not causal.
    """

    incident: dict[str, list[tuple[str, KnowledgeGraphPathHop]]] = defaultdict(list)
    for edge in edges:
        weight = float(edge.edge_weight)
        if not (weight > 0 and weight == weight):
            continue
        source = node_key(edge.source_node_type_code, edge.source_node_id)
        target = node_key(edge.target_node_type_code, edge.target_node_id)
        incident[source].append(
            (
                target,
                KnowledgeGraphPathHop(
                    from_node_type_code=edge.source_node_type_code,
                    from_node_id=edge.source_node_id,
                    edge_type_code=edge.edge_type_code,
                    to_node_type_code=edge.target_node_type_code,
                    to_node_id=edge.target_node_id,
                    traversal_direction="forward",
                    edge_weight=weight,
                ),
            )
        )
        incident[target].append(
            (
                source,
                KnowledgeGraphPathHop(
                    from_node_type_code=edge.target_node_type_code,
                    from_node_id=edge.target_node_id,
                    edge_type_code=edge.edge_type_code,
                    to_node_type_code=edge.source_node_type_code,
                    to_node_id=edge.source_node_id,
                    traversal_direction="reverse",
                    edge_weight=weight,
                ),
            )
        )
    for hops in incident.values():
        hops.sort(
            key=lambda item: (
                -item[1].edge_weight,
                item[1].edge_type_code,
                item[1].to_node_type_code,
                item[1].to_node_id,
                item[1].traversal_direction,
            )
        )

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
        "semantic shortest paths",
    )

    replace_once(
        BACKEND_GRAPH,
        "from lineageweave.ontology import ontology_annotations\n",
        "from lineageweave.ontology import ontology_annotations, relationship_annotations\n",
        "backend relationship annotation import",
    )
    replace_once(
        BACKEND_GRAPH,
        "    select_related_nodes,\n)\n",
        "    select_related_nodes,\n    semantic_paths_from_edges,\n)\n",
        "backend semantic path import",
    )
    replace_once(
        BACKEND_GRAPH,
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
                "from_node_id": hop.from_node_id,
                "to_node_type_code": hop.to_node_type_code,
                "to_node_id": hop.to_node_id,
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
        "buyer semantic path payload",
    )

    replace_once(
        API_TYPES,
        "export interface RelatedNode {\n",
        '''export interface SemanticPathHop {
  from_node_type_code: RelatedNodeType | string;
  from_node_id: string;
  to_node_type_code: RelatedNodeType | string;
  to_node_id: string;
  edge_type_code: string;
  traversal_direction: "forward" | "reverse";
  relationship_iri?: string;
  relationship_label?: string;
}

export interface RelatedNode {
''',
        "frontend semantic path type",
    )
    replace_once(
        API_TYPES,
        "  ontology_label?: string;\n}\n\nexport interface PostRoleResponsibility",
        "  ontology_label?: string;\n  semantic_path?: SemanticPathHop[];\n}\n\nexport interface PostRoleResponsibility",
        "related node semantic path",
    )

    write(
        FRONTEND_COMPONENT,
        '''import type { SemanticPathHop } from "../api";
import { t } from "../i18n";

export function semanticPathText(semanticPath?: SemanticPathHop[]): string {
  const labels = (semanticPath ?? [])
    .map((hop) => t(hop.relationship_label ?? hop.edge_type_code))
    .filter((label) => label.length > 0);
  return labels.length > 0 ? labels.join(" → ") : t("Graph relation");
}

export function RelatedSemanticPath({
  semanticPath,
  className = "related-post-kind",
}: {
  semanticPath?: SemanticPathHop[];
  className?: string;
}) {
  const text = semanticPathText(semanticPath);
  return (
    <span className={className} title={text}>
      {text}
    </span>
  );
}
''',
    )

    replace_once(
        APP,
        'import { PopupCloseButton } from "./components/PopupCloseButton";\n',
        'import { PopupCloseButton } from "./components/PopupCloseButton";\nimport { RelatedSemanticPath } from "./components/RelatedSemanticPath";\n',
        "semantic path component import",
    )
    replace_once(
        APP,
        '<span className="related-post-kind">{t("Graph relation")}</span>',
        '<RelatedSemanticPath semanticPath={node.semantic_path} />',
        "related post semantic path",
    )
    replace_once(
        APP,
        '''                    >
                      {caption}
                    </button>
                  </li>
                );
              case NODE_CORPORATE_ENTITY:
''',
        '''                    >
                      {caption}
                    </button>
                    <RelatedSemanticPath semanticPath={node.semantic_path} />
                  </li>
                );
              case NODE_CORPORATE_ENTITY:
''',
        "related person semantic path",
    )
    replace_once(
        APP,
        '''                    >
                      {caption}
                    </button>
                  </li>
                );
              case NODE_TEAM:
''',
        '''                    >
                      {caption}
                    </button>
                    <RelatedSemanticPath semanticPath={node.semantic_path} />
                  </li>
                );
              case NODE_TEAM:
''',
        "related entity semantic path",
    )
    replace_once(
        APP,
        '''                    >
                      {caption}
                    </button>
                  </li>
                );
              default: {
''',
        '''                    >
                      {caption}
                    </button>
                    <RelatedSemanticPath semanticPath={node.semantic_path} />
                  </li>
                );
              default: {
''',
        "related team semantic path",
    )
    replace_once(
        APP,
        '''                <li key={`${node.node_type_code}:${node.node_id}`}>
                  {relatedNodeCaption(node)}
                </li>
''',
        '''                <li key={`${node.node_type_code}:${node.node_id}`}>
                  {relatedNodeCaption(node)}
                  <RelatedSemanticPath semanticPath={node.semantic_path} />
                </li>
''',
        "landed related semantic path",
    )

    replace_once(
        ONTOLOGY_TEST,
        "from rdflib.namespace import RDFS, SKOS\n",
        "from rdflib.namespace import OWL, RDFS, SKOS\n",
        "ontology inverse import",
    )
    replace_once(
        ONTOLOGY_TEST,
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
        "ontology direction regression",
    )
    replace_once(
        PROJECTION_TEST,
        '''        assert first_post_id in related_ids
        assert second_post_id in related_ids
        hydrated = await hydrate_related_nodes(
''',
        '''        assert first_post_id in related_ids
        assert second_post_id in related_ids
        related_by_id = {node["node_id"]: node for node in related}
        assert related_by_id[first_post_id]["semantic_path"] == [
            {
                "from_node_type_code": NODE_TEAM,
                "from_node_id": team_id,
                "to_node_type_code": NODE_POST,
                "to_node_id": first_post_id,
                "edge_type_code": EDGE_MENTION_TEAM,
                "traversal_direction": "forward",
                "relationship_iri": "https://contextualwisdomlab.github.io/lineageweave/ontology#mentionsTeam",
                "relationship_label": "mentioned in post",
            }
        ]
        hydrated = await hydrate_related_nodes(
''',
        "real PostgreSQL semantic path regression",
    )

    adr_path = next_adr_path()
    write(
        adr_path,
        f'''# ADR {adr_path.name[:4]}: Ontology-grounded semantic relationship paths

## Status

Accepted

## Context

The Buyer related-node surface ranked evidence-gated knowledge-graph nodes with random walk with restart, but returned only each node class and a numeric relevance score. The relationship predicates traversed from the selected person, team, organization, or post disappeared, so the UI could only say `Graph relation`. The ontology also declared `edge_mention` as `Post -> Person`, while the canonical relational projection stores `Person -> Post`.

## Decision

- Keep the existing canonical `knowledge_graph_edge` direction.
- Correct the OWL domain/range for `edge_mention` to `Person -> Post` and declare explicit `owl:inverseOf` properties for direction-correct buyer traversal.
- Compute a deterministic shortest semantic path over the same positive, ABAC- and evidence-gated subgraph used by RWR. RWR still determines relevance; the path explains stored connectivity and is not a causal claim.
- Return every hop's endpoint identifiers, lookup code, traversal direction, ontology IRI, and ontology label. Unknown ontology terms remain absent rather than receiving guessed labels.
- Render the relationship path for post, person, team, and organization results.

## Consequences

The API change is additive. Existing consumers may ignore `semantic_path`. PostgreSQL remains the system of record; OWL supplies controlled terms and inverse semantics. A future RDF 1.2 export may annotate individual assertions with provenance, but this slice does not claim RDF 1.2 conformance or create unsupported facts.
''',
    )
    write(
        DOCTORING,
        '''# Semantic relationship path references

## Product traceability

- `knowledge_graph_edge` is interpreted as a typed subject-predicate-object assertion whose canonical direction must match the OWL property's domain and range.
- `owl:inverseOf` supplies the predicate used when the buyer traverses a stored assertion in reverse.
- `knowledge_graph_edge_evidence` continues to gate the visible subgraph; semantic paths never bypass ABAC or invent provenance.
- RDF 1.2 triple terms and annotations are tracked for a future interoperable statement-provenance export; PostgreSQL remains authoritative in this release.

## APA 7th references

World Wide Web Consortium. (2012). *OWL 2 Web Ontology Language: Document overview (Second Edition).* https://www.w3.org/TR/owl2-overview/

World Wide Web Consortium. (2013). *PROV-O: The PROV ontology.* https://www.w3.org/TR/prov-o/

World Wide Web Consortium. (2026). *RDF 1.2 concepts and abstract data model* (Candidate Recommendation Snapshot, April 7, 2026). https://www.w3.org/TR/rdf12-concepts/
''',
    )
    write(
        CHANGELOG,
        '''### Fixed

- Aligned `edge_mention` OWL domain/range with the canonical Person-to-Post graph direction and added explicit inverse relationship terms.
- Related knowledge-graph nodes now carry and render a deterministic ontology relationship path explaining why each buyer-visible result is connected.
''',
    )


def main() -> None:
    """Dispatch the RED or GREEN phase."""

    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("red", "apply"))
    args = parser.parse_args()
    if args.mode == "red":
        write_red()
    else:
        apply()


if __name__ == "__main__":
    main()
