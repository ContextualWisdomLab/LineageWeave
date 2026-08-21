"""Load the versioned LineageWeave Knowledge Graph ontology.

``docs/ontology/lineageweave-kg.ttl`` is the formal OWL 2, RDFS, SKOS,
W3C Organization Ontology, and PROV-O vocabulary for navigation node and
edge types plus the controlled vocabularies backed by
``common_lookup_value``. Real corporate entities use W3C ORG; SKOS is
reserved for classifications and labels such as Group, Company, and Plant.

PostgreSQL remains the source of record for graph data. This module is the
single application boundary for resolving a stored lookup code to its
canonical ontology IRI. The companion
``docs/ontology/lineageweave-kg.shacl.ttl`` publishes closed-world RDF
cardinality constraints for external consumers; database constraints and
RBAC/ABAC remain authoritative for product storage and disclosure.

``tests/test_ontology.py`` checks lookup-code round trips, while
``tests/test_ontology_interoperability.py`` checks the ORG/SKOS separation,
version/import metadata, and SHACL contract.
"""

from __future__ import annotations

from pathlib import Path

from rdflib import Graph, Namespace
from rdflib.namespace import OWL, RDF, RDFS, SKOS
from rdflib.term import Identifier

#: The ontology's own namespace -- every class/property IRI below is
#: this prefix plus the term's local name (e.g. LW.Post).
LW = Namespace("https://contextualwisdomlab.github.io/lineageweave/ontology#")

#: The custom annotation property linking an ontology term to the exact
#: `common_lookup_value.lookup_code` string it corresponds to.
LOOKUP_CODE = LW.lookupCode

_ONTOLOGY_PATH = Path(__file__).resolve().parents[1] / "docs" / "ontology" / "lineageweave-kg.ttl"


def load_ontology() -> Graph:
    """Parse the committed core Turtle ontology into a fresh RDF graph.

    External ``owl:imports`` are metadata only. ``rdflib`` parses the local
    committed artifact and this function performs no network dereference.
    Callers that need repeated access should use the module-level
    :data:`ONTOLOGY` singleton or cache the returned graph.
    """
    graph = Graph()
    graph.parse(_ONTOLOGY_PATH, format="turtle")
    return graph


#: Parsed once at import time -- the ontology file changes only when a
#: developer edits it, never at runtime.
ONTOLOGY = load_ontology()


def _term_subject(lookup_code: str) -> Identifier | None:
    """Return the ontology term annotated with ``lookup_code``, if present."""
    for subject in ONTOLOGY.subjects(LOOKUP_CODE, None):
        if str(ONTOLOGY.value(subject, LOOKUP_CODE)) == lookup_code:
            return subject
    return None


def iri_for_lookup_code(lookup_code: str) -> str | None:
    """Return the canonical ontology IRI for one relational lookup code.

    ``None`` means the ontology deliberately does not cover that code, for
    example a workflow status vocabulary outside this semantic profile.
    """
    subject = _term_subject(lookup_code)
    return str(subject) if subject is not None else None


def ontology_annotations(lookup_code: str) -> dict[str, str]:
    """Return the IRI and label for a declared lookup code.

    An undeclared code returns an empty mapping rather than a fabricated
    semantic label, preserving the product's missing-versus-negative
    distinction.
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
    """Return every relational lookup code declared by the ontology."""
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
