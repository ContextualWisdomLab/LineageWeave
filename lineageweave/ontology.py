"""Loads `docs/ontology/lineageweave-kg.ttl` -- the formal OWL 2 / RDFS /
SKOS vocabulary (ADR 0004) for `knowledge_graph_edge`'s node/edge types
and the `entity_relationship_type` / `person_side` / `corporate_entity_level`
controlled vocabularies in `migrations/0001_initial_schema.sql`.

PostgreSQL stays the source of record for actual graph data; this module
is the single place application code gets a canonical IRI for a
`common_lookup_value.lookup_code`, instead of re-typing the lookup code
as a bare string wherever the ontology's vocabulary matters. The Turtle
file itself is the semantic-layer artifact -- see the ADR for why that
is the correct, standards-grounded reading of "semantic layer" here
rather than a separate BI-metrics concept.

`tests/test_ontology.py` is the real correctness check: it loads the
same file with `rdflib` and asserts every lookup code the relational
schema actually defines has a matching ontology term, and vice versa.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from urllib.parse import quote
from uuid import UUID

from rdflib import Graph, Literal, Namespace, URIRef
from rdflib.namespace import OWL, PROV, RDF, RDFS, SKOS, XSD
from rdflib.term import Identifier

from .post_summary import normalize_project_key, project_candidate_node_id

#: The ontology's own namespace -- every class/property IRI below is
#: this prefix plus the term's local name (e.g. LW.Post). ADR 0207 made
#: the repository-case spelling canonical (it is the exact path GitHub
#: Pages serves) and demoted the lowercase form to a deprecated
#: compatibility vocabulary.
LW = Namespace("https://contextualwisdomlab.github.io/LineageWeave/ontology#")

#: The custom annotation property linking an ontology term to the exact
#: `common_lookup_value.lookup_code` string it corresponds to.
LOOKUP_CODE = LW.lookupCode

_ONTOLOGY_PATH = Path(__file__).resolve().parents[1] / "docs" / "ontology" / "lineageweave-kg.ttl"


def load_ontology() -> Graph:
    """Parses `docs/ontology/lineageweave-kg.ttl` fresh. Callers that
    need it repeatedly should cache the result themselves (see
    `ONTOLOGY` below for the module-level singleton); this function
    exists separately so tests can load a fresh graph without relying
    on import-time caching.
    """
    graph = Graph()
    graph.parse(_ONTOLOGY_PATH, format="turtle")
    return graph


#: Parsed once at import time -- the ontology file changes only when a
#: developer edits it, never at runtime.
ONTOLOGY = load_ontology()


def _term_subject(lookup_code: str) -> Identifier | None:
    """Implement the _term_subject operation for this channel."""
    for subject in ONTOLOGY.subjects(LOOKUP_CODE, None):
        if str(ONTOLOGY.value(subject, LOOKUP_CODE)) == lookup_code:
            return subject
    return None


def iri_for_lookup_code(lookup_code: str) -> str | None:
    """The ontology term IRI whose `:lookupCode` annotation equals
    `lookup_code`, or `None` if no term declares that code -- e.g. a
    `common_lookup_value` category this ontology doesn't cover yet
    (`ticket_status`, `post_visibility`), which is a real, expected gap,
    not a bug.
    """
    subject = _term_subject(lookup_code)
    return str(subject) if subject is not None else None


def ontology_annotations(lookup_code: str) -> dict[str, str]:
    """IRI plus its RDFS or SKOS preferred label, or empty if undeclared.

    Empty (not a fabricated label) when the ontology does not cover
    this code -- the same missing-vs-negative discipline as Null
    channels. Callers spread this onto an API payload.
    """
    subject = _term_subject(lookup_code)
    if subject is None:
        return {}
    fields = {"ontology_iri": str(subject)}
    label = ONTOLOGY.value(subject, RDFS.label) or ONTOLOGY.value(subject, SKOS.prefLabel)
    if label is None:
        raise ValueError(f"ontology term for {lookup_code!r} has no readable label")
    fields["ontology_label"] = str(label)
    return fields


def all_declared_lookup_codes() -> set[str]:
    """Every `common_lookup_value.lookup_code` string this ontology
    declares a term for, across all categories -- used by
    `tests/test_ontology.py` to round-trip against the live schema.
    """
    return {str(value) for value in ONTOLOGY.objects(None, LOOKUP_CODE)}


def ontology_node_iri(node_type_code: str, node_id: str) -> str:
    """Return the canonical percent-encoded IRI for one ontology node."""

    if not node_type_code or not node_id:
        raise ValueError("ontology node type and id must be non-empty")
    return str(
        LW[
            f"node/{quote(node_type_code, safe='')}/"
            f"{quote(node_id, safe='/')}"
        ]
    )


def project_source_post_rdf(
    *,
    post_id: str,
    post_title: str,
    post_body: str,
    post_created_at: datetime,
    voc_type_code: str,
    source_stage_code: str | None = None,
    source_detail_state_code: str | None = None,
) -> Graph:
    """Project one authorized ``source_post`` row without interpreting raw codes."""
    canonical_post_id = str(UUID(post_id))
    if not post_title.strip():
        raise ValueError("post_title must be non-empty")
    if post_created_at.tzinfo is None or post_created_at.utcoffset() is None:
        raise ValueError("post_created_at must be timezone-aware")
    post_type = _term_subject(voc_type_code)
    if post_type is None or (post_type, SKOS.inScheme, LW.postTypeScheme) not in ONTOLOGY:
        raise ValueError("voc_type_code must name a governed post type")
    post = URIRef(ontology_node_iri("node_post", canonical_post_id))
    graph = Graph()
    graph.bind("lw", LW)
    graph.add((post, RDF.type, LW.Post))
    graph.add((post, LW.postTitle, Literal(post_title)))
    graph.add((post, LW.postBody, Literal(post_body)))
    graph.add((post, LW.bodyAvailable, Literal(bool(post_body.strip()), datatype=XSD.boolean)))
    graph.add((post, LW.hasPostType, post_type))
    graph.add((post, LW.createdAt, Literal(post_created_at, datatype=XSD.dateTime)))
    for predicate, value in (
        (LW.sourceStageCode, source_stage_code),
        (LW.sourceDetailStateCode, source_detail_state_code),
    ):
        if value is not None:
            if not value.strip():
                raise ValueError("source classification codes must be non-empty when provided")
            graph.add((post, predicate, Literal(value)))
    return graph


def project_project_mention_rdf(
    *,
    post_id: str,
    post_title: str,
    post_body: str,
    post_created_at: datetime,
    voc_type_code: str,
    project_key: str,
    project_name: str,
    evidence_text: str,
    confidence: Decimal | float | str,
    mention_created_at: datetime,
) -> Graph:
    """Project one authorized joined Post/Project-mention row to RDF.

    PostgreSQL remains authoritative. The caller supplies one already
    authorized row; this pure projection preserves the direct assertion and
    its SHACL-governed reification without querying or mutating a data store.
    """
    canonical_post_id = str(UUID(post_id))
    if normalize_project_key(project_key) != project_key:
        raise ValueError("project_key must already be normalized")
    for field_name, value in (
        ("project_name", project_name),
        ("evidence_text", evidence_text),
    ):
        if not value.strip():
            raise ValueError(f"{field_name} must be non-empty")
    for field_name, value in (
        ("post_created_at", post_created_at),
        ("mention_created_at", mention_created_at),
    ):
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError(f"{field_name} must be timezone-aware")
    try:
        confidence_value = Decimal(str(confidence))
    except InvalidOperation as exc:
        raise ValueError("confidence must be a decimal between zero and one") from exc
    if not confidence_value.is_finite() or not Decimal(0) <= confidence_value <= Decimal(1):
        raise ValueError("confidence must be a decimal between zero and one")

    post = URIRef(ontology_node_iri("node_post", canonical_post_id))
    candidate_id = project_candidate_node_id(canonical_post_id, project_key)
    project = URIRef(ontology_node_iri("node_project", candidate_id))
    mention = URIRef(
        LW[f"statement/project-mention/{canonical_post_id}/{quote(project_key, safe='')}"]
    )
    graph = project_source_post_rdf(
        post_id=canonical_post_id,
        post_title=post_title,
        post_body=post_body,
        post_created_at=post_created_at,
        voc_type_code=voc_type_code,
    )
    graph.bind("prov", PROV)
    graph.add((project, RDF.type, LW.Project))
    graph.add((project, RDFS.label, Literal(project_name)))
    graph.add((post, LW.mentionsProject, project))
    graph.add((mention, RDF.type, LW.ProjectMention))
    graph.add((mention, RDF.subject, post))
    graph.add((mention, RDF.predicate, LW.mentionsProject))
    graph.add((mention, RDF.object, project))
    graph.add((mention, LW.projectEvidence, Literal(evidence_text)))
    graph.add((mention, LW.semanticConfidence, Literal(confidence_value, datatype=XSD.decimal)))
    graph.add((mention, PROV.wasDerivedFrom, post))
    graph.add((mention, PROV.generatedAtTime, Literal(mention_created_at, datatype=XSD.dateTime)))
    return graph


__all__ = [
    "LOOKUP_CODE",
    "LW",
    "ONTOLOGY",
    "OWL",
    "RDF",
    "RDFS",
    "SKOS",
    "all_declared_lookup_codes",
    "iri_for_lookup_code",
    "load_ontology",
    "ontology_node_iri",
    "ontology_annotations",
    "project_project_mention_rdf",
    "project_source_post_rdf",
]
