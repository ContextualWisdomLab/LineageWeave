"""Bounded ontology/provenance neighborhood (ADR 0184 / issue #341).

PostgreSQL remains authoritative. This module only assembles a typed,
authorization-already-applied graph for GET /api/ontology/neighborhood.
Event Lineage (reconstructed post-to-post parents) is a different surface
and is never mixed in.

Grounding: RDF 1.1 Concepts (Cyganiak, Wood, & Lanthaler, 2014); RDF
Schema 1.1 (Brickley & Guha, 2014); OWL 2 (W3C, 2012); SKOS (Miles &
Bechhofer, 2009); PROV-O (Lebo, Sahoo, & McGuinness, 2013); OWL-Time
(Cox & Little, 2022); JSON-LD 1.1 (Kellogg, Champin, & Longley, 2020).
"""

from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass, replace
from datetime import datetime
from typing import Mapping, Sequence

from lineageweave.knowledge_graph import (
    EDGE_AFFILIATION,
    EDGE_CO_MENTION,
    EDGE_MENTION,
    EDGE_MENTION_ORGANIZATION,
    EDGE_MENTION_PROJECT,
    EDGE_MENTION_TEAM,
    EDGE_TEAM_AFFILIATION,
    NODE_CORPORATE_ENTITY,
    NODE_PERSON,
    NODE_POST,
    NODE_PROJECT,
    NODE_TEAM,
)
from lineageweave.ontology import LW, ontology_annotations, ontology_node_iri

TRUTH_AUTHORITATIVE = "truth_authoritative"
TRUTH_OBSERVED = "truth_observed"
TRUTH_INFERRED = "truth_inferred"
TRUTH_PROPOSED = "truth_proposed"
TRUTH_SUPERSEDED = "truth_superseded"
TRUTH_REJECTED = "truth_rejected"

TRUTH_STATUS_CODES = frozenset(
    {
        TRUTH_AUTHORITATIVE,
        TRUTH_OBSERVED,
        TRUTH_INFERRED,
        TRUTH_PROPOSED,
        TRUTH_SUPERSEDED,
        TRUTH_REJECTED,
    }
)

PROPERTY_MENTIONS = "mentions"
PROPERTY_AFFILIATED_WITH = "affiliatedWith"
PROPERTY_CO_MENTIONED_WITH = "coMentionedWith"
PROPERTY_MENTIONS_TEAM = "mentionsTeam"
PROPERTY_TEAM_AFFILIATED_WITH = "teamAffiliatedWith"
PROPERTY_MENTIONS_ORGANIZATION = "mentionsOrganization"
PROPERTY_MENTIONS_PROJECT = "mentionsProject"
PROPERTY_SKOS_BROADER = "skos_broader"
PROPERTY_OWL_SUBCLASS_OF = "owl_subclass_of"

SKOS_BROADER_IRI = "http://www.w3.org/2004/02/skos/core#broader"
JSONLD_CONTEXT = {
    "lw": str(LW),
    "skos": "http://www.w3.org/2004/02/skos/core#",
    "owl": "http://www.w3.org/2002/07/owl#",
    "prov": "http://www.w3.org/ns/prov#",
    "rdfs": "http://www.w3.org/2000/01/rdf-schema#",
    "time": "http://www.w3.org/2006/time#",
    "xsd": "http://www.w3.org/2001/XMLSchema#",
}

KNOWN_NODE_TYPES = frozenset(
    {NODE_POST, NODE_PERSON, NODE_CORPORATE_ENTITY, NODE_TEAM, NODE_PROJECT}
)
_KG_PROPERTY_BY_EDGE = {
    EDGE_MENTION: PROPERTY_MENTIONS,
    EDGE_AFFILIATION: PROPERTY_AFFILIATED_WITH,
    EDGE_CO_MENTION: PROPERTY_CO_MENTIONED_WITH,
    EDGE_MENTION_TEAM: PROPERTY_MENTIONS_TEAM,
    EDGE_TEAM_AFFILIATION: PROPERTY_TEAM_AFFILIATED_WITH,
    EDGE_MENTION_ORGANIZATION: PROPERTY_MENTIONS_ORGANIZATION,
    EDGE_MENTION_PROJECT: PROPERTY_MENTIONS_PROJECT,
}
_PROPERTY_IRI = {
    PROPERTY_MENTIONS: str(LW.mentions),
    PROPERTY_AFFILIATED_WITH: str(LW.affiliatedWith),
    PROPERTY_CO_MENTIONED_WITH: str(LW.coMentionedWith),
    PROPERTY_MENTIONS_TEAM: str(LW.mentionsTeam),
    PROPERTY_TEAM_AFFILIATED_WITH: str(LW.teamAffiliatedWith),
    PROPERTY_MENTIONS_ORGANIZATION: str(LW.mentionsOrganization),
    PROPERTY_MENTIONS_PROJECT: str(LW.mentionsProject),
    PROPERTY_SKOS_BROADER: SKOS_BROADER_IRI,
}
INSTANCE_PROPERTY_CODES = frozenset(_PROPERTY_IRI)
ALLOWED_PROPERTY_ALIASES = {
    **{code: code for code in INSTANCE_PROPERTY_CODES},
    EDGE_MENTION: PROPERTY_MENTIONS,
    EDGE_AFFILIATION: PROPERTY_AFFILIATED_WITH,
    EDGE_CO_MENTION: PROPERTY_CO_MENTIONED_WITH,
    EDGE_MENTION_TEAM: PROPERTY_MENTIONS_TEAM,
    EDGE_TEAM_AFFILIATION: PROPERTY_TEAM_AFFILIATED_WITH,
    EDGE_MENTION_ORGANIZATION: PROPERTY_MENTIONS_ORGANIZATION,
    EDGE_MENTION_PROJECT: PROPERTY_MENTIONS_PROJECT,
}

DEFAULT_MAXIMUM_DEPTH = 2
DEFAULT_MAXIMUM_NODES = 40
DEFAULT_MAXIMUM_EDGES = 80
HARD_MAXIMUM_DEPTH = 8
HARD_MAXIMUM_NODES = 200
HARD_MAXIMUM_EDGES = 400

NODE_SHAPE = {
    NODE_POST: "rectangle",
    NODE_PERSON: "ellipse",
    NODE_CORPORATE_ENTITY: "hexagon",
    NODE_TEAM: "rounded-rectangle",
    NODE_PROJECT: "diamond",
}


class OntologyNeighborhoodError(ValueError):
    """Fail-closed contract violation for the ontology neighborhood."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


@dataclass(frozen=True)
class NeighborhoodFact:
    """One typed instance fact supplied by the application layer.

    Endpoints must already exist. Authorization and source eligibility
    are the caller's job; this assembler never invents a node, a
    property, or a truth promotion.
    """

    source_node_type_code: str
    source_node_id: str
    target_node_type_code: str
    target_node_id: str
    property_code: str
    truth_status_code: str
    recorded_at: datetime
    valid_from: datetime | None = None
    valid_to: datetime | None = None
    evidence_references: tuple[str, ...] = ()
    provenance_reference: str | None = None
    # SQL source windows already computed this relation's focus distance. It
    # is internal paging metadata, not buyer-facing evidence.
    source_hop_depth: int | None = None
    # The SQL keyset order is retained separately from display orientation.
    # It keeps source-window page selection and continuation on one order.
    source_order_key: tuple[int, str, str, str, str, str] | None = None


@dataclass(frozen=True)
class OntologyGraphNode:
    """One heterogeneous ontology node in the bounded neighborhood."""

    node_id: str
    node_type_code: str
    ontology_class_iri: str
    display_label: str
    truth_status_code: str | None
    valid_from: datetime | None
    valid_to: datetime | None
    recorded_at: datetime | None
    evidence_count: int
    shape_code: str


@dataclass(frozen=True)
class OntologyNodeMetadata:
    """Catalog-owned metadata for one heterogeneous ontology node.

    ``None`` means the catalog has not supplied that value. Edge metadata is
    never used as a substitute because doing so changes a node's meaning when
    pagination or filtering changes.
    """

    truth_status_code: str | None = None
    recorded_at: datetime | None = None


@dataclass(frozen=True)
class OntologyGraphEdge:
    """One typed ontology/KG edge in the bounded neighborhood."""

    edge_id: str
    source_node_type_code: str
    source_node_id: str
    target_node_type_code: str
    target_node_id: str
    property_code: str
    ontology_property_iri: str
    property_label: str
    truth_status_code: str
    valid_from: datetime | None
    valid_to: datetime | None
    recorded_at: datetime
    provenance_reference: str | None
    evidence_references: tuple[str, ...]


@dataclass(frozen=True)
class OntologyNeighborhood:
    """Bounded, deterministic neighborhood payload."""

    focus_node_id: str
    focus_node_type_code: str
    nodes: tuple[OntologyGraphNode, ...]
    edges: tuple[OntologyGraphEdge, ...]
    truncated: bool
    next_cursor: str | None
    limitation_code: str | None

    def exact_value_rows(self) -> tuple[dict[str, str], ...]:
        """Keyboard/print/CSV rows for the same visible graph."""
        rows: list[dict[str, str]] = []
        labels = {(node.node_type_code, node.node_id): node.display_label for node in self.nodes}
        for edge in self.edges:
            rows.append(
                {
                    "edge_id": edge.edge_id,
                    "source_node_id": edge.source_node_id,
                    "source_label": _label_for(labels, edge.source_node_type_code, edge.source_node_id),
                    "source_type_code": edge.source_node_type_code,
                    "property_code": edge.property_code,
                    "property_label": edge.property_label,
                    "ontology_property_iri": edge.ontology_property_iri,
                    "target_node_id": edge.target_node_id,
                    "target_label": _label_for(labels, edge.target_node_type_code, edge.target_node_id),
                    "target_type_code": edge.target_node_type_code,
                    "truth_status_code": edge.truth_status_code,
                    "recorded_at": edge.recorded_at.isoformat(),
                    "valid_from": edge.valid_from.isoformat() if edge.valid_from else "",
                    "valid_to": edge.valid_to.isoformat() if edge.valid_to else "",
                    "evidence_count": str(len(edge.evidence_references)),
                }
            )
        return tuple(rows)

    def jsonld_document(self) -> dict[str, object]:
        """JSON-LD 1.1 projection of the visible neighborhood only."""
        graph: list[dict[str, object]] = []
        for node in self.nodes:
            item: dict[str, object] = {
                "@id": ontology_node_iri(node.node_type_code, node.node_id),
                "@type": node.ontology_class_iri,
                "rdfs:label": node.display_label,
                "lw:nodeType": node.node_type_code,
            }
            _add_jsonld_times(item, node.recorded_at, node.valid_from, node.valid_to)
            graph.append(item)
            if node.truth_status_code is not None:
                graph[-1]["lw:truthStatus"] = node.truth_status_code
        for edge in self.edges:
            item: dict[str, object] = {
                "@id": f"lw:edge/{edge.edge_id}",
                "@type": "prov:Entity",
                edge.ontology_property_iri: {
                    "@id": ontology_node_iri(
                        _node_type_for(
                            self.nodes,
                            edge.target_node_type_code,
                            edge.target_node_id,
                        ),
                        edge.target_node_id,
                    )
                },
                "prov:wasDerivedFrom": [
                    {"@id": f"lw:evidence/{reference}"} for reference in edge.evidence_references
                ],
                "lw:truthStatus": edge.truth_status_code,
                "lw:source": {
                    "@id": ontology_node_iri(
                        _node_type_for(
                            self.nodes,
                            edge.source_node_type_code,
                            edge.source_node_id,
                        ),
                        edge.source_node_id,
                    )
                },
            }
            _add_jsonld_times(item, edge.recorded_at, edge.valid_from, edge.valid_to)
            graph.append(item)
        return {"@context": JSONLD_CONTEXT, "@graph": graph}


def _add_jsonld_times(
    item: dict[str, object],
    recorded_at: datetime | None,
    valid_from: datetime | None,
    valid_to: datetime | None,
) -> None:
    """Add only available PROV-O system time and OWL-Time validity bounds."""

    def _instant(value: datetime) -> dict[str, object]:
        return {
            "@type": "time:Instant",
            "time:inXSDDateTimeStamp": {
                "@value": value.isoformat(),
                "@type": "xsd:dateTimeStamp",
            },
        }

    if recorded_at is not None:
        item["prov:generatedAtTime"] = {
            "@value": recorded_at.isoformat(),
            "@type": "xsd:dateTimeStamp",
        }
    if valid_from is not None:
        item["time:hasBeginning"] = _instant(valid_from)
    if valid_to is not None:
        item["time:hasEnd"] = _instant(valid_to)


def _node_type_for(
    nodes: Sequence[OntologyGraphNode], node_type_code: str, node_id: str
) -> str:
    for node in nodes:
        if node.node_type_code == node_type_code and node.node_id == node_id:
            return node.node_type_code
    raise OntologyNeighborhoodError("dangling_endpoint", "visible edge references a missing node")


def _label_for(labels: Mapping[tuple[str, str], str], node_type_code: str, node_id: str) -> str:
    """Return a visible endpoint label, or fail closed like JSON-LD."""
    label = labels.get((node_type_code, node_id))
    if label is None:
        raise OntologyNeighborhoodError("dangling_endpoint", "visible edge references a missing node")
    return label


def canonicalize_property_code(property_code: str) -> str:
    """Map a lookup/edge alias onto the instance property code, or fail."""
    if property_code == PROPERTY_OWL_SUBCLASS_OF:
        raise OntologyNeighborhoodError(
            "owl_subclass_not_instance",
            "OWL class subsumption is schema, not an instance neighborhood edge",
        )
    canonical = ALLOWED_PROPERTY_ALIASES.get(property_code)
    if canonical is None:
        raise OntologyNeighborhoodError("unknown_property", f"unknown property {property_code!r}")
    return canonical


def fact_from_knowledge_graph_edge(
    *,
    source_node_type_code: str,
    source_node_id: str,
    target_node_type_code: str,
    target_node_id: str,
    edge_type_code: str,
    recorded_at: datetime,
    evidence_references: Sequence[str] = (),
    provenance_reference: str | None = None,
    truth_status_code: str = TRUTH_OBSERVED,
) -> NeighborhoodFact:
    """Project one ``knowledge_graph_edge`` onto a display-direction fact.

    ``edge_mention`` is stored Person --mentionedIn--> Post. The buyer
    neighborhood uses the declared inverse ``mentions`` so the required
    path is Post --mentions--> Person --affiliatedWith--> CorporateEntity.
    """
    property_code = _KG_PROPERTY_BY_EDGE.get(edge_type_code)
    if property_code is None:
        raise OntologyNeighborhoodError("unknown_property", f"unknown edge type {edge_type_code!r}")
    src_type, src_id, dst_type, dst_id = (
        source_node_type_code,
        source_node_id,
        target_node_type_code,
        target_node_id,
    )
    if edge_type_code == EDGE_MENTION:
        src_type, src_id, dst_type, dst_id = (
            target_node_type_code,
            target_node_id,
            source_node_type_code,
            source_node_id,
        )
    return NeighborhoodFact(
        source_node_type_code=src_type,
        source_node_id=src_id,
        target_node_type_code=dst_type,
        target_node_id=dst_id,
        property_code=property_code,
        truth_status_code=truth_status_code,
        recorded_at=recorded_at,
        evidence_references=tuple(evidence_references),
        provenance_reference=provenance_reference,
    )


def skos_broader_fact(
    *,
    narrower_entity_id: str,
    broader_entity_id: str,
    recorded_at: datetime,
    provenance_reference: str | None = None,
) -> NeighborhoodFact:
    """Catalog parent as SKOS broader, never as OWL subclass."""
    return NeighborhoodFact(
        source_node_type_code=NODE_CORPORATE_ENTITY,
        source_node_id=narrower_entity_id,
        target_node_type_code=NODE_CORPORATE_ENTITY,
        target_node_id=broader_entity_id,
        property_code=PROPERTY_SKOS_BROADER,
        truth_status_code=TRUTH_AUTHORITATIVE,
        recorded_at=recorded_at,
        provenance_reference=provenance_reference,
    )


def _node_key(node_type_code: str, node_id: str) -> str:
    return f"{node_type_code}:{node_id}"


def _edge_id(fact: NeighborhoodFact) -> str:
    return (
        f"{fact.property_code}:{fact.source_node_type_code}:{fact.source_node_id}:"
        f"{fact.target_node_type_code}:{fact.target_node_id}"
    )


def _property_label(property_code: str) -> str:
    if property_code == PROPERTY_SKOS_BROADER:
        return "broader"
    annotations = ontology_annotations(
        {
            PROPERTY_MENTIONS: EDGE_MENTION,
            PROPERTY_AFFILIATED_WITH: EDGE_AFFILIATION,
            PROPERTY_CO_MENTIONED_WITH: EDGE_CO_MENTION,
            PROPERTY_MENTIONS_TEAM: EDGE_MENTION_TEAM,
            PROPERTY_TEAM_AFFILIATED_WITH: EDGE_TEAM_AFFILIATION,
            PROPERTY_MENTIONS_ORGANIZATION: EDGE_MENTION_ORGANIZATION,
            PROPERTY_MENTIONS_PROJECT: EDGE_MENTION_PROJECT,
        }[property_code]
    )
    return annotations.get("ontology_label", property_code)


def assemble_ontology_neighborhood(
    *,
    focus_node_type_code: str,
    focus_node_id: str,
    facts: Sequence[NeighborhoodFact],
    labels: Mapping[tuple[str, str], str],
    node_metadata: Mapping[tuple[str, str], OntologyNodeMetadata] | None = None,
    hidden_node_keys: frozenset[str] = frozenset(),
    knowledge_cutoff: datetime | None = None,
    maximum_depth: int = DEFAULT_MAXIMUM_DEPTH,
    maximum_nodes: int = DEFAULT_MAXIMUM_NODES,
    maximum_edges: int = DEFAULT_MAXIMUM_EDGES,
    allowed_property_codes: Sequence[str] | None = None,
    cursor: str | None = None,
    source_truncated: bool = False,
) -> OntologyNeighborhood:
    """Walk a bounded typed neighborhood from an already-visible focus.

    Hidden endpoints remove the edge. Truncation never reports how many
    neighbors were omitted. OWL subclass facts are rejected. Inferred
    facts stay inferred. A bounded loader can set ``source_truncated`` so
    an exhausted in-memory page never masquerades as the complete graph.
    """
    if focus_node_type_code not in KNOWN_NODE_TYPES:
        raise OntologyNeighborhoodError("unknown_node_type", f"unknown node type {focus_node_type_code!r}")
    if not focus_node_id or focus_node_id.strip() != focus_node_id:
        raise OntologyNeighborhoodError("invalid_focus_id", "focus node id is empty or padded")
    if maximum_depth < 1 or maximum_depth > HARD_MAXIMUM_DEPTH:
        raise OntologyNeighborhoodError("excessive_depth", "neighborhood depth is out of bounds")
    if maximum_nodes < 1 or maximum_nodes > HARD_MAXIMUM_NODES:
        raise OntologyNeighborhoodError("unbounded_request", "neighborhood node bound is out of range")
    if maximum_edges < 1 or maximum_edges > HARD_MAXIMUM_EDGES:
        raise OntologyNeighborhoodError("unbounded_request", "neighborhood edge bound is out of range")
    if cursor is not None and not cursor.startswith("after:"):
        raise OntologyNeighborhoodError("malformed_cursor", "cursor must be an opaque after: token")

    allowed: frozenset[str] | None
    if allowed_property_codes is None:
        allowed = None
    else:
        allowed = frozenset(canonicalize_property_code(code) for code in allowed_property_codes)

    focus_key = _node_key(focus_node_type_code, focus_node_id)
    if focus_key in hidden_node_keys:
        raise OntologyNeighborhoodError("focus_hidden", "focus node is not visible")
    if (focus_node_type_code, focus_node_id) not in labels:
        raise OntologyNeighborhoodError("dangling_endpoint", "focus node has no authorized label")

    visible_facts: list[NeighborhoodFact] = []
    for fact in facts:
        _validate_fact(fact)
        property_code = canonicalize_property_code(fact.property_code)
        if allowed is not None and property_code not in allowed:
            continue
        if knowledge_cutoff is not None and fact.recorded_at > knowledge_cutoff:
            continue
        if fact.valid_from is not None and knowledge_cutoff is not None and fact.valid_from > knowledge_cutoff:
            continue
        if fact.valid_to is not None and knowledge_cutoff is not None and fact.valid_to < knowledge_cutoff:
            continue
        source_key = _node_key(fact.source_node_type_code, fact.source_node_id)
        target_key = _node_key(fact.target_node_type_code, fact.target_node_id)
        if source_key in hidden_node_keys or target_key in hidden_node_keys:
            continue
        if (fact.source_node_type_code, fact.source_node_id) not in labels:
            continue
        if (fact.target_node_type_code, fact.target_node_id) not in labels:
            continue
        visible_facts.append(
            NeighborhoodFact(
                source_node_type_code=fact.source_node_type_code,
                source_node_id=fact.source_node_id,
                target_node_type_code=fact.target_node_type_code,
                target_node_id=fact.target_node_id,
                property_code=property_code,
                truth_status_code=fact.truth_status_code,
                recorded_at=fact.recorded_at,
                valid_from=fact.valid_from,
                valid_to=fact.valid_to,
                evidence_references=fact.evidence_references,
                provenance_reference=fact.provenance_reference,
                source_hop_depth=fact.source_hop_depth,
                source_order_key=fact.source_order_key,
            )
        )

    adjacency: dict[str, list[NeighborhoodFact]] = defaultdict(list)
    for fact in visible_facts:
        adjacency[_node_key(fact.source_node_type_code, fact.source_node_id)].append(fact)
        adjacency[_node_key(fact.target_node_type_code, fact.target_node_id)].append(fact)

    reached: dict[str, int] = {focus_key: 0}
    collected: list[NeighborhoodFact] = []
    seen_edges: set[str] = set()
    source_window_facts = [
        fact
        for fact in visible_facts
        if fact.source_hop_depth is not None or fact.source_order_key is not None
    ]
    if source_window_facts:
        # A source-cursor page may begin after the focus edge. PostgreSQL has
        # already performed the authorized recursive BFS, so replay its
        # bounded hop metadata instead of requiring the page to contain the
        # earlier bridge facts.
        deduplicated: dict[str, NeighborhoodFact] = {}
        def source_page_sort_key(
            fact: NeighborhoodFact,
        ) -> tuple[int, tuple[int, str, str, str, str, str]]:
            """Order source-window facts by their opaque cursor key, falling
            back to a deterministic hop/property/node tuple for facts the
            cursor page did not carry a position for."""
            if fact.source_order_key is not None:
                return (0, fact.source_order_key)
            return (
                1,
                (
                    fact.source_hop_depth
                    if fact.source_hop_depth is not None
                    else maximum_depth,
                    fact.property_code,
                    fact.source_node_type_code,
                    fact.source_node_id,
                    fact.target_node_type_code,
                    fact.target_node_id,
                ),
            )

        for fact in sorted(visible_facts, key=source_page_sort_key):
            edge_id = _edge_id(fact)
            existing = deduplicated.get(edge_id)
            if existing is None:
                deduplicated[edge_id] = fact
                continue
            hop_depths = [
                depth
                for depth in (existing.source_hop_depth, fact.source_hop_depth)
                if depth is not None
            ]
            deduplicated[edge_id] = replace(
                existing,
                recorded_at=min(existing.recorded_at, fact.recorded_at),
                evidence_references=tuple(
                    sorted(set(existing.evidence_references) | set(fact.evidence_references))
                ),
                source_hop_depth=min(hop_depths) if hop_depths else None,
                source_order_key=min(
                    key
                    for key in (existing.source_order_key, fact.source_order_key)
                    if key is not None
                )
                if existing.source_order_key is not None or fact.source_order_key is not None
                else None,
            )
        collected = list(deduplicated.values())
        for fact in collected:
            seen_edges.add(_edge_id(fact))
            depth = fact.source_hop_depth if fact.source_hop_depth is not None else maximum_depth
            for endpoint in (
                _node_key(fact.source_node_type_code, fact.source_node_id),
                _node_key(fact.target_node_type_code, fact.target_node_id),
            ):
                reached.setdefault(endpoint, depth + 1)
    else:
        queue: deque[str] = deque([focus_key])
        while queue:
            current = queue.popleft()
            depth = reached[current]
            if depth >= maximum_depth:
                continue
            for fact in sorted(adjacency.get(current, ()), key=_fact_sort_key):
                edge_id = _edge_id(fact)
                if edge_id in seen_edges:
                    continue
                seen_edges.add(edge_id)
                collected.append(fact)
                for endpoint in (
                    _node_key(fact.source_node_type_code, fact.source_node_id),
                    _node_key(fact.target_node_type_code, fact.target_node_id),
                ):
                    if endpoint not in reached:
                        reached[endpoint] = depth + 1
                        queue.append(endpoint)

    start = 0
    if cursor is not None:
        token = cursor.removeprefix("after:")
        matched = next(
            (index for index, fact in enumerate(collected) if _edge_id(fact) == token),
            None,
        )
        if matched is None:
            raise OntologyNeighborhoodError("malformed_cursor", "cursor does not name a visible edge")
        start = matched + 1

    page_edges = collected[start : start + maximum_edges]
    truncated = source_truncated or (start + len(page_edges)) < len(collected) or len(reached) > maximum_nodes
    next_cursor = None
    if (start + len(page_edges)) < len(collected) and page_edges:
        next_cursor = f"after:{_edge_id(page_edges[-1])}"

    catalog_metadata = node_metadata or {}
    for metadata in catalog_metadata.values():
        if (
            metadata.truth_status_code is not None
            and metadata.truth_status_code not in TRUTH_STATUS_CODES
        ):
            raise OntologyNeighborhoodError(
                "unknown_truth_status", "node truth status is not governed"
            )
        if metadata.recorded_at is not None and metadata.recorded_at.tzinfo is None:
            raise OntologyNeighborhoodError(
                "naive_timestamp", "node recorded_at must be offset-aware"
            )
    node_evidence: dict[str, set[str]] = defaultdict(set)
    node_meta: dict[str, tuple[str, str, str | None, datetime | None]] = {}
    focus_label = labels[(focus_node_type_code, focus_node_id)]
    focus_metadata = catalog_metadata.get((focus_node_type_code, focus_node_id), OntologyNodeMetadata())
    node_meta[focus_key] = (
        focus_node_type_code,
        focus_label,
        focus_metadata.truth_status_code,
        focus_metadata.recorded_at,
    )
    for fact in page_edges:
        for node_type, node_id in (
            (fact.source_node_type_code, fact.source_node_id),
            (fact.target_node_type_code, fact.target_node_id),
        ):
            key = _node_key(node_type, node_id)
            label = labels[(node_type, node_id)]
            node_evidence[key].update(fact.evidence_references)
            current = node_meta.get(key)
            if current is None:
                metadata = catalog_metadata.get((node_type, node_id), OntologyNodeMetadata())
                node_meta[key] = (
                    node_type,
                    label,
                    metadata.truth_status_code,
                    metadata.recorded_at,
                )

    # Trim by proximity to the focus (BFS/source-hop distance in `reached`),
    # not by the "type:id" key string -- otherwise farther nodes of an
    # alphabetically-earlier type code survive over closer nodes of a later
    # type code. Node key is only a tiebreaker for equal distance.
    ordered_keys = [focus_key] + sorted(
        (key for key in node_meta if key != focus_key),
        key=lambda key: (reached.get(key, maximum_depth + 1), key),
    )
    if len(ordered_keys) > maximum_nodes:
        keep = set(ordered_keys[:maximum_nodes])
        page_edges = [
            fact
            for fact in page_edges
            if _node_key(fact.source_node_type_code, fact.source_node_id) in keep
            and _node_key(fact.target_node_type_code, fact.target_node_id) in keep
        ]
        ordered_keys = [key for key in ordered_keys if key in keep]
        truncated = True
        next_cursor = None
        node_evidence = defaultdict(set)
        for fact in page_edges:
            for node_type, node_id in (
                (fact.source_node_type_code, fact.source_node_id),
                (fact.target_node_type_code, fact.target_node_id),
            ):
                node_evidence[_node_key(node_type, node_id)].update(
                    fact.evidence_references
                )

    nodes = tuple(
        OntologyGraphNode(
            node_id=key.split(":", 1)[1],
            node_type_code=node_meta[key][0],
            ontology_class_iri=ontology_annotations(node_meta[key][0]).get(
                "ontology_iri", str(LW[node_meta[key][0]])
            ),
            display_label=node_meta[key][1],
            truth_status_code=node_meta[key][2],
            valid_from=None,
            valid_to=None,
            recorded_at=node_meta[key][3],
            evidence_count=len(node_evidence.get(key, set())),
            shape_code=NODE_SHAPE[node_meta[key][0]],
        )
        for key in ordered_keys
    )
    edges = tuple(
        OntologyGraphEdge(
            edge_id=_edge_id(fact),
            source_node_type_code=fact.source_node_type_code,
            source_node_id=fact.source_node_id,
            target_node_type_code=fact.target_node_type_code,
            target_node_id=fact.target_node_id,
            property_code=fact.property_code,
            ontology_property_iri=_PROPERTY_IRI[fact.property_code],
            property_label=_property_label(fact.property_code),
            truth_status_code=fact.truth_status_code,
            valid_from=fact.valid_from,
            valid_to=fact.valid_to,
            recorded_at=fact.recorded_at,
            provenance_reference=fact.provenance_reference,
            evidence_references=fact.evidence_references,
        )
        for fact in page_edges
    )
    limitation = "neighborhood_truncated" if truncated else None
    if not edges and focus_key in node_meta:
        limitation = limitation or "neighborhood_empty"
    return OntologyNeighborhood(
        focus_node_id=focus_node_id,
        focus_node_type_code=focus_node_type_code,
        nodes=nodes,
        edges=edges,
        truncated=truncated,
        next_cursor=next_cursor,
        limitation_code=limitation,
    )


def _validate_fact(fact: NeighborhoodFact) -> None:
    if fact.source_node_type_code not in KNOWN_NODE_TYPES or fact.target_node_type_code not in KNOWN_NODE_TYPES:
        raise OntologyNeighborhoodError("unknown_node_type", "fact uses an unknown node type")
    if fact.truth_status_code not in TRUTH_STATUS_CODES:
        raise OntologyNeighborhoodError("unknown_truth_status", f"unknown truth {fact.truth_status_code!r}")
    if fact.recorded_at.tzinfo is None:
        raise OntologyNeighborhoodError("naive_timestamp", "recorded_at must be offset-aware")
    if fact.valid_from is not None and fact.valid_from.tzinfo is None:
        raise OntologyNeighborhoodError("naive_timestamp", "valid_from must be offset-aware")
    if fact.valid_to is not None and fact.valid_to.tzinfo is None:
        raise OntologyNeighborhoodError("naive_timestamp", "valid_to must be offset-aware")
    if fact.valid_from is not None and fact.valid_to is not None and fact.valid_to < fact.valid_from:
        raise OntologyNeighborhoodError("invalid_interval", "valid_to precedes valid_from")
    if fact.property_code == PROPERTY_OWL_SUBCLASS_OF:
        raise OntologyNeighborhoodError(
            "owl_subclass_not_instance",
            "OWL class subsumption is not an instance neighborhood edge",
        )


def _fact_sort_key(fact: NeighborhoodFact) -> tuple[str, str, str, str, str]:
    return (
        fact.property_code,
        fact.source_node_id,
        fact.target_node_id,
        fact.source_node_type_code,
        fact.target_node_type_code,
    )


__all__ = [
    "ALLOWED_PROPERTY_ALIASES",
    "DEFAULT_MAXIMUM_DEPTH",
    "DEFAULT_MAXIMUM_EDGES",
    "DEFAULT_MAXIMUM_NODES",
    "INSTANCE_PROPERTY_CODES",
    "JSONLD_CONTEXT",
    "NeighborhoodFact",
    "NODE_SHAPE",
    "OntologyGraphEdge",
    "OntologyGraphNode",
    "OntologyNodeMetadata",
    "OntologyNeighborhood",
    "OntologyNeighborhoodError",
    "PROPERTY_AFFILIATED_WITH",
    "PROPERTY_CO_MENTIONED_WITH",
    "PROPERTY_MENTIONS",
    "PROPERTY_MENTIONS_ORGANIZATION",
    "PROPERTY_MENTIONS_PROJECT",
    "PROPERTY_MENTIONS_TEAM",
    "PROPERTY_OWL_SUBCLASS_OF",
    "PROPERTY_SKOS_BROADER",
    "PROPERTY_TEAM_AFFILIATED_WITH",
    "SKOS_BROADER_IRI",
    "TRUTH_AUTHORITATIVE",
    "TRUTH_INFERRED",
    "TRUTH_OBSERVED",
    "TRUTH_PROPOSED",
    "TRUTH_REJECTED",
    "TRUTH_STATUS_CODES",
    "TRUTH_SUPERSEDED",
    "assemble_ontology_neighborhood",
    "canonicalize_property_code",
    "fact_from_knowledge_graph_edge",
    "skos_broader_fact",
]
