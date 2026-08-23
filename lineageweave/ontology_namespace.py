"""Canonical vs repository-case public ontology namespace (ADR 0158).

GitHub Pages project paths are case-sensitive (GitHub, 2024). This
repository therefore currently publishes two distinct IRI prefixes:

- Canonical knowledge-graph namespace used by runtime lookup, API
  payloads, and persisted evidence:
  ``https://contextualwisdomlab.github.io/lineageweave/ontology#``
- Repository-case PROV-O support-profile prefix used by
  ``docs/ontology/prov-o-support-profile.ttl``:
  ``https://contextualwisdomlab.github.io/LineageWeave/ontology#``

A documentation HTTP redirect is not RDF identity (Cyganiak, Wood, &
Lanthaler, 2014, section 3.2). Both namespace documents are documented
as ``200 OK`` publications; the lowercase document is authoritative.
This module inventories both prefixes, maps only class terms that share
a local name *and* term kind, and never rewrites stored evidence.

References
----------
Cyganiak, R., Wood, D., & Lanthaler, M. (Eds.). (2014). *RDF 1.1
concepts and abstract syntax*. World Wide Web Consortium.
https://www.w3.org/TR/rdf11-concepts/

GitHub. (2024). *About GitHub Pages*. GitHub Docs.
https://docs.github.com/en/pages/getting-started-with-github-pages/about-github-pages

Miles, A., & Bechhofer, S. (Eds.). (2009). *SKOS simple knowledge
organization system reference*. World Wide Web Consortium.
https://www.w3.org/TR/skos-reference/

Sauermann, L., & Cyganiak, R. (2008). *Cool URIs for the Semantic Web*
(W3C Interest Group Note). World Wide Web Consortium.
https://www.w3.org/TR/cooluris/

W3C OWL Working Group. (2012). *OWL 2 web ontology language document
overview* (2nd ed.). World Wide Web Consortium.
https://www.w3.org/TR/owl2-overview/
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from rdflib import Graph, URIRef
from rdflib.namespace import OWL, RDF, RDFS

CANONICAL_ONTOLOGY_NAMESPACE = (
    "https://contextualwisdomlab.github.io/lineageweave/ontology#"
)
DEPRECATED_PAGES_ONTOLOGY_NAMESPACE = (
    "https://contextualwisdomlab.github.io/LineageWeave/ontology#"
)
CANONICAL_ONTOLOGY_DOCUMENT_IRI = (
    "https://contextualwisdomlab.github.io/lineageweave/ontology"
)
DEPRECATED_PAGES_ONTOLOGY_DOCUMENT_IRI = (
    "https://contextualwisdomlab.github.io/LineageWeave/ontology"
)
PROV_O_SUPPORT_DOCUMENT_IRI = (
    "https://contextualwisdomlab.github.io/LineageWeave/prov-o-support"
)

#: Local names that are owl:Class (or rdfs:subClassOf, which entails a
#: class) in *both* the KG ontology and the PROV-O support profile.
COMPATIBLE_CLASS_LOCAL_NAMES = frozenset(
    {"Post", "Person", "CorporateEntity", "Team"}
)

_REPO_ROOT = Path(__file__).resolve().parents[1]
_KG_PATH = _REPO_ROOT / "docs" / "ontology" / "lineageweave-kg.ttl"
_PROV_O_PROFILE_PATH = (
    _REPO_ROOT / "docs" / "ontology" / "prov-o-support-profile.ttl"
)
_COMPATIBILITY_PATH = (
    _REPO_ROOT / "docs" / "ontology" / "namespace-compatibility.ttl"
)

TermKind = Literal[
    "class",
    "object_property",
    "datatype_property",
    "annotation_property",
    "concept",
    "other",
]


@dataclass(frozen=True, slots=True)
class NamespaceTerm:
    """One IRI published under a LineageWeave ontology prefix.

    ``term_kind`` is the RDF/OWL metaclass of the resource, never a
    guessed label. A class in one graph is not equivalent to a property
    in the other even when the local name matches.
    """

    iri: str
    local_name: str
    namespace: str
    term_kind: TermKind


@dataclass(frozen=True, slots=True)
class NamespaceHttpBehavior:
    """Documented HTTP contract for a public ontology IRI (ADR 0158).

    Both namespace documents are specified as ``200 OK``. Live GitHub
    Pages dereference is out of band for CI: the in-repository Turtle
    path is the source artifact. A redirect is explicitly *not* RDF
    identity and is not the documented publication status.
    """

    requested_iri: str
    documentation_role: Literal[
        "canonical_kg", "deprecated_pages_alias", "prov_o_support", "unknown"
    ]
    in_repository_turtle: str | None
    rdf_identity_from_redirect: bool
    documented_http_status: Literal[200] | None


def _term_kind(graph: Graph, subject: URIRef) -> TermKind:
    """Classify ``subject`` by RDF/OWL term kind, fail-closed to other."""
    types = set(graph.objects(subject, RDF.type))
    if OWL.Class in types or RDFS.Class in types:
        return "class"
    if OWL.ObjectProperty in types:
        return "object_property"
    if OWL.DatatypeProperty in types:
        return "datatype_property"
    if OWL.AnnotationProperty in types:
        return "annotation_property"
    if any(str(value).endswith("Concept") for value in types):
        return "concept"
    if any(True for _ in graph.objects(subject, RDFS.subClassOf)):
        return "class"
    return "other"


def classify_term_kind(graph: Graph, iri: str) -> TermKind:
    """Public fail-closed classifier used by compatibility mapping."""
    return _term_kind(graph, URIRef(iri))


def _local_name(iri: str, namespace: str) -> str:
    """Return the fragment after ``namespace``, or empty when absent."""
    if not iri.startswith(namespace):
        return ""
    return iri[len(namespace) :]


def _terms_for_graph(graph: Graph, namespace: str) -> tuple[NamespaceTerm, ...]:
    """Inventory subjects published under ``namespace``."""
    terms: list[NamespaceTerm] = []
    seen: set[str] = set()
    for subject in graph.subjects():
        iri = str(subject)
        if iri in seen or not iri.startswith(namespace):
            continue
        local_name = _local_name(iri, namespace)
        if not local_name:
            continue
        seen.add(iri)
        terms.append(
            NamespaceTerm(
                iri=iri,
                local_name=local_name,
                namespace=namespace,
                term_kind=_term_kind(graph, subject),
            )
        )
    return tuple(sorted(terms, key=lambda term: term.iri))


def load_knowledge_graph_ontology() -> Graph:
    """Parse the canonical lowercase KG ontology Turtle file."""
    graph = Graph()
    graph.parse(_KG_PATH, format="turtle")
    return graph


def load_prov_o_support_profile() -> Graph:
    """Parse the repository-case PROV-O support profile Turtle file."""
    graph = Graph()
    graph.parse(_PROV_O_PROFILE_PATH, format="turtle")
    return graph


def load_namespace_compatibility() -> Graph:
    """Parse the published compatibility vocabulary."""
    graph = Graph()
    graph.parse(_COMPATIBILITY_PATH, format="turtle")
    return graph


def inventory_namespace_terms() -> tuple[NamespaceTerm, ...]:
    """Return every IRI fragment published under either ontology prefix.

    The two ontology *documents* are not the same resource: the
    lowercase document is the KG vocabulary, the repository-case
    ``prov-o-support`` document is a PROV-O alignment profile.
    """
    kg_terms = _terms_for_graph(
        load_knowledge_graph_ontology(), CANONICAL_ONTOLOGY_NAMESPACE
    )
    profile_terms = _terms_for_graph(
        load_prov_o_support_profile(), DEPRECATED_PAGES_ONTOLOGY_NAMESPACE
    )
    return kg_terms + profile_terms


def compatible_class_pairs() -> tuple[tuple[str, str], ...]:
    """Return (canonical, deprecated) IRI pairs that share class kind.

    Pairs are restricted to ``COMPATIBLE_CLASS_LOCAL_NAMES``. A matching
    local name of a different term kind is omitted rather than mapped.
    """
    by_ns_and_name: dict[tuple[str, str], NamespaceTerm] = {
        (term.namespace, term.local_name): term
        for term in inventory_namespace_terms()
    }
    pairs: list[tuple[str, str]] = []
    for local_name in sorted(COMPATIBLE_CLASS_LOCAL_NAMES):
        canonical = by_ns_and_name.get((CANONICAL_ONTOLOGY_NAMESPACE, local_name))
        deprecated = by_ns_and_name.get(
            (DEPRECATED_PAGES_ONTOLOGY_NAMESPACE, local_name)
        )
        if (
            canonical is None
            or deprecated is None
            or canonical.term_kind != "class"
            or deprecated.term_kind != "class"
        ):
            continue
        pairs.append((canonical.iri, deprecated.iri))
    return tuple(pairs)


def canonical_iri(iri: str) -> str | None:
    """Map a known ontology IRI onto the canonical lowercase form.

    Canonical IRIs return themselves. The four compatible class IRIs
    under the repository-case prefix map to the KG class. Any other
    repository-case fragment, an unknown prefix, or an empty local name
    returns ``None`` rather than inventing a term. Stored evidence is
    never rewritten by this function.
    """
    if iri.startswith(CANONICAL_ONTOLOGY_NAMESPACE):
        local_name = _local_name(iri, CANONICAL_ONTOLOGY_NAMESPACE)
        return iri if local_name else None
    if iri.startswith(DEPRECATED_PAGES_ONTOLOGY_NAMESPACE):
        local_name = _local_name(iri, DEPRECATED_PAGES_ONTOLOGY_NAMESPACE)
        if local_name in COMPATIBLE_CLASS_LOCAL_NAMES:
            return f"{CANONICAL_ONTOLOGY_NAMESPACE}{local_name}"
        return None
    return None


def migrate_stored_iri(iri: str) -> str:
    """Return ``iri`` unchanged unless it is a mapped class alias.

    Historical KG IRIs stay byte-identical. Only the four published
    class aliases rewrite to the canonical form. Unknown aliases raise
    ``ValueError`` so a bulk migrator cannot silently invent terms.
    The function is idempotent and does not write a database row.
    """
    document_iris = {
        CANONICAL_ONTOLOGY_DOCUMENT_IRI,
        DEPRECATED_PAGES_ONTOLOGY_DOCUMENT_IRI,
        PROV_O_SUPPORT_DOCUMENT_IRI,
        CANONICAL_ONTOLOGY_NAMESPACE.rstrip("#"),
        DEPRECATED_PAGES_ONTOLOGY_NAMESPACE.rstrip("#"),
    }
    if iri.rstrip("#") in document_iris or iri in {
        CANONICAL_ONTOLOGY_NAMESPACE,
        DEPRECATED_PAGES_ONTOLOGY_NAMESPACE,
    }:
        raise ValueError("ontology document IRI is not a term")
    if iri.startswith(CANONICAL_ONTOLOGY_NAMESPACE):
        if not _local_name(iri, CANONICAL_ONTOLOGY_NAMESPACE):
            raise ValueError("ontology document IRI is not a term")
        return iri
    mapped = canonical_iri(iri)
    if mapped is None:
        raise ValueError(f"unmapped ontology IRI: {iri}")
    return mapped


def documentation_http_behavior(iri: str) -> NamespaceHttpBehavior:
    """Return the documented HTTP contract for a public ontology IRI.

    Live network dereference is out of band. Both public documents are
    specified as ``200 OK``. The in-repository Turtle file is the source
    of truth; a Pages redirect must not be treated as ``owl:sameAs``.
    """
    if iri == CANONICAL_ONTOLOGY_DOCUMENT_IRI or iri.startswith(
        CANONICAL_ONTOLOGY_NAMESPACE
    ):
        return NamespaceHttpBehavior(
            requested_iri=iri,
            documentation_role="canonical_kg",
            in_repository_turtle="docs/ontology/lineageweave-kg.ttl",
            rdf_identity_from_redirect=False,
            documented_http_status=200,
        )
    if iri == PROV_O_SUPPORT_DOCUMENT_IRI:
        return NamespaceHttpBehavior(
            requested_iri=iri,
            documentation_role="prov_o_support",
            in_repository_turtle="docs/ontology/prov-o-support-profile.ttl",
            rdf_identity_from_redirect=False,
            documented_http_status=200,
        )
    if iri == DEPRECATED_PAGES_ONTOLOGY_DOCUMENT_IRI or iri.startswith(
        DEPRECATED_PAGES_ONTOLOGY_NAMESPACE
    ):
        return NamespaceHttpBehavior(
            requested_iri=iri,
            documentation_role="deprecated_pages_alias",
            in_repository_turtle="docs/ontology/namespace-compatibility.ttl",
            rdf_identity_from_redirect=False,
            documented_http_status=200,
        )
    return NamespaceHttpBehavior(
        requested_iri=iri,
        documentation_role="unknown",
        in_repository_turtle=None,
        rdf_identity_from_redirect=False,
        documented_http_status=None,
    )


__all__ = [
    "CANONICAL_ONTOLOGY_DOCUMENT_IRI",
    "CANONICAL_ONTOLOGY_NAMESPACE",
    "COMPATIBLE_CLASS_LOCAL_NAMES",
    "DEPRECATED_PAGES_ONTOLOGY_DOCUMENT_IRI",
    "DEPRECATED_PAGES_ONTOLOGY_NAMESPACE",
    "PROV_O_SUPPORT_DOCUMENT_IRI",
    "NamespaceHttpBehavior",
    "NamespaceTerm",
    "canonical_iri",
    "classify_term_kind",
    "compatible_class_pairs",
    "documentation_http_behavior",
    "inventory_namespace_terms",
    "load_knowledge_graph_ontology",
    "load_namespace_compatibility",
    "load_prov_o_support_profile",
    "migrate_stored_iri",
]
