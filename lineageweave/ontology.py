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

from pathlib import Path

from rdflib import Graph, Namespace
from rdflib.namespace import OWL, RDF, RDFS, SKOS
from rdflib.term import Identifier

#: The ontology's own namespace -- every class/property IRI below is
#: this prefix plus the term's local name (e.g. LW.Post). ADR 0205 made
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
    """IRI + ``rdfs:label`` for a lookup code, or empty if undeclared.

    Empty (not a fabricated label) when the ontology does not cover
    this code -- the same missing-vs-negative discipline as Null
    channels. Callers spread this onto an API payload.
    """
    subject = _term_subject(lookup_code)
    if subject is None:
        return {}
    fields = {"ontology_iri": str(subject)}
    label = ONTOLOGY.value(subject, RDFS.label)
    if label is not None:
        fields["ontology_label"] = str(label)
    return fields


def all_declared_lookup_codes() -> set[str]:
    """Every `common_lookup_value.lookup_code` string this ontology
    declares a term for, across all categories -- used by
    `tests/test_ontology.py` to round-trip against the live schema.
    """
    return {str(value) for value in ONTOLOGY.objects(None, LOOKUP_CODE)}


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
    "ontology_annotations",
]
