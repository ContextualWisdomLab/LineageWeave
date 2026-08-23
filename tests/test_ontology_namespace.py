"""Contract tests for the canonical vs repository-case ontology namespace.

These tests are file-and-RDF-level. They do not rewrite stored evidence
and they do not require a live GitHub Pages fetch.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from rdflib import OWL, URIRef, Graph
from rdflib.namespace import RDF, RDFS, SKOS

from lineageweave.ontology import LW
from lineageweave.ontology_namespace import (
    CANONICAL_ONTOLOGY_DOCUMENT_IRI,
    CANONICAL_ONTOLOGY_NAMESPACE,
    COMPATIBLE_CLASS_LOCAL_NAMES,
    DEPRECATED_PAGES_ONTOLOGY_DOCUMENT_IRI,
    DEPRECATED_PAGES_ONTOLOGY_NAMESPACE,
    PROV_O_SUPPORT_DOCUMENT_IRI,
    canonical_iri,
    classify_term_kind,
    compatible_class_pairs,
    documentation_http_behavior,
    inventory_namespace_terms,
    load_knowledge_graph_ontology,
    load_namespace_compatibility,
    load_prov_o_support_profile,
    migrate_stored_iri,
)

_REPO_ROOT = Path(__file__).resolve().parents[1]


def test_runtime_lw_namespace_stays_canonical_lowercase() -> None:
    assert str(LW) == CANONICAL_ONTOLOGY_NAMESPACE
    assert CANONICAL_ONTOLOGY_NAMESPACE != DEPRECATED_PAGES_ONTOLOGY_NAMESPACE
    assert not str(LW).startswith(DEPRECATED_PAGES_ONTOLOGY_NAMESPACE)


def test_inventory_contains_both_public_namespace_forms() -> None:
    terms = inventory_namespace_terms()
    namespaces = {term.namespace for term in terms}
    assert CANONICAL_ONTOLOGY_NAMESPACE in namespaces
    assert DEPRECATED_PAGES_ONTOLOGY_NAMESPACE in namespaces
    local_names = {(term.namespace, term.local_name) for term in terms}
    for local_name in COMPATIBLE_CLASS_LOCAL_NAMES:
        assert (CANONICAL_ONTOLOGY_NAMESPACE, local_name) in local_names
        assert (DEPRECATED_PAGES_ONTOLOGY_NAMESPACE, local_name) in local_names


def test_compatible_pairs_are_classes_with_matching_local_names() -> None:
    pairs = compatible_class_pairs()
    assert {canonical.rsplit("#", 1)[-1] for canonical, _ in pairs} == set(
        COMPATIBLE_CLASS_LOCAL_NAMES
    )
    for canonical, deprecated in pairs:
        assert canonical.startswith(CANONICAL_ONTOLOGY_NAMESPACE)
        assert deprecated.startswith(DEPRECATED_PAGES_ONTOLOGY_NAMESPACE)
        assert canonical.rsplit("#", 1)[-1] == deprecated.rsplit("#", 1)[-1]


def test_compatibility_graph_uses_equivalent_class_only_for_mapped_classes() -> None:
    graph = load_namespace_compatibility()
    mapped = {
        (str(subject), str(obj))
        for subject, obj in graph.subject_objects(OWL.equivalentClass)
    }
    expected = set(compatible_class_pairs())
    assert mapped == expected
    assert (
        URIRef(CANONICAL_ONTOLOGY_DOCUMENT_IRI),
        OWL.sameAs,
        URIRef(DEPRECATED_PAGES_ONTOLOGY_DOCUMENT_IRI),
    ) not in graph
    assert (
        URIRef(CANONICAL_ONTOLOGY_DOCUMENT_IRI),
        OWL.sameAs,
        URIRef(PROV_O_SUPPORT_DOCUMENT_IRI),
    ) not in graph


def test_unmatched_kg_fragments_are_not_equivalent_classes() -> None:
    graph = load_namespace_compatibility()
    equivalent_objects = {
        str(obj)
        for obj in graph.objects(
            URIRef(f"{CANONICAL_ONTOLOGY_NAMESPACE}OurSidePerson"),
            OWL.equivalentClass,
        )
    }
    assert not equivalent_objects
    mentioned = {
        str(obj)
        for obj in graph.objects(
            URIRef(f"{CANONICAL_ONTOLOGY_NAMESPACE}mentionedIn"),
            OWL.equivalentProperty,
        )
    }
    assert not mentioned


def test_canonical_iri_is_identity_for_historical_kg_terms() -> None:
    historical = f"{CANONICAL_ONTOLOGY_NAMESPACE}Post"
    assert canonical_iri(historical) == historical
    assert migrate_stored_iri(historical) == historical
    assert migrate_stored_iri(migrate_stored_iri(historical)) == historical


def test_canonical_iri_maps_only_compatible_class_aliases() -> None:
    assert (
        canonical_iri(f"{DEPRECATED_PAGES_ONTOLOGY_NAMESPACE}Team")
        == f"{CANONICAL_ONTOLOGY_NAMESPACE}Team"
    )
    assert canonical_iri(f"{DEPRECATED_PAGES_ONTOLOGY_NAMESPACE}OurSidePerson") is None
    assert canonical_iri(f"{DEPRECATED_PAGES_ONTOLOGY_NAMESPACE}mentionedIn") is None
    assert canonical_iri("https://example.invalid/ontology#Post") is None
    assert canonical_iri(CANONICAL_ONTOLOGY_NAMESPACE) is None


def test_migrate_stored_iri_fails_closed_on_unknown_alias() -> None:
    with pytest.raises(ValueError, match="unmapped ontology IRI"):
        migrate_stored_iri(f"{DEPRECATED_PAGES_ONTOLOGY_NAMESPACE}OurSidePerson")
    with pytest.raises(ValueError, match="ontology document IRI"):
        migrate_stored_iri(CANONICAL_ONTOLOGY_DOCUMENT_IRI)
    with pytest.raises(ValueError, match="ontology document IRI"):
        migrate_stored_iri(DEPRECATED_PAGES_ONTOLOGY_DOCUMENT_IRI)
    with pytest.raises(ValueError, match="ontology document IRI"):
        migrate_stored_iri(PROV_O_SUPPORT_DOCUMENT_IRI)

    with pytest.raises(ValueError, match="unmapped ontology IRI"):
        migrate_stored_iri("https://example.invalid/ontology#Post")


def test_migrate_stored_iri_is_idempotent_for_mapped_alias() -> None:
    alias = f"{DEPRECATED_PAGES_ONTOLOGY_NAMESPACE}Person"
    once = migrate_stored_iri(alias)
    assert once == f"{CANONICAL_ONTOLOGY_NAMESPACE}Person"
    assert migrate_stored_iri(once) == once


def test_documentation_http_behavior_never_treats_redirect_as_rdf_identity() -> None:
    canonical = documentation_http_behavior(f"{CANONICAL_ONTOLOGY_NAMESPACE}Post")
    alias = documentation_http_behavior(f"{DEPRECATED_PAGES_ONTOLOGY_NAMESPACE}Post")
    support = documentation_http_behavior(PROV_O_SUPPORT_DOCUMENT_IRI)
    unknown = documentation_http_behavior("https://example.invalid/ontology#Post")
    assert canonical.documentation_role == "canonical_kg"
    assert alias.documentation_role == "deprecated_pages_alias"
    assert support.documentation_role == "prov_o_support"
    assert unknown.documentation_role == "unknown"
    for behavior in (canonical, alias, support):
        assert behavior.rdf_identity_from_redirect is False
        assert behavior.documented_http_status == 200
    assert unknown.documented_http_status is None
    assert unknown.rdf_identity_from_redirect is False
    assert (_REPO_ROOT / canonical.in_repository_turtle).is_file()
    assert (_REPO_ROOT / alias.in_repository_turtle).is_file()
    assert (_REPO_ROOT / support.in_repository_turtle).is_file()


def test_document_iris_are_specified_as_http_200() -> None:
    for iri in (
        CANONICAL_ONTOLOGY_DOCUMENT_IRI,
        DEPRECATED_PAGES_ONTOLOGY_DOCUMENT_IRI,
        PROV_O_SUPPORT_DOCUMENT_IRI,
    ):
        behavior = documentation_http_behavior(iri)
        assert behavior.documented_http_status == 200
        assert behavior.rdf_identity_from_redirect is False


def test_in_repository_turtle_files_parse_for_both_namespace_forms() -> None:
    kg = load_knowledge_graph_ontology()
    profile = load_prov_o_support_profile()
    assert (URIRef(CANONICAL_ONTOLOGY_DOCUMENT_IRI), RDF.type, OWL.Ontology) in kg
    assert (URIRef(PROV_O_SUPPORT_DOCUMENT_IRI), RDF.type, OWL.Ontology) in profile
    for local_name in COMPATIBLE_CLASS_LOCAL_NAMES:
        assert URIRef(f"{CANONICAL_ONTOLOGY_NAMESPACE}{local_name}") in {
            subject for subject in kg.subjects()
        }
        assert URIRef(f"{DEPRECATED_PAGES_ONTOLOGY_NAMESPACE}{local_name}") in {
            subject for subject in profile.subjects()
        }


def test_compatibility_graph_is_isomorphic_across_reloads() -> None:
    first = load_namespace_compatibility()
    second = load_namespace_compatibility()
    assert first.isomorphic(second)


def test_classify_term_kind_is_fail_closed_and_kind_specific() -> None:
    graph = Graph()
    owl_class = URIRef("https://example.invalid/ontology#OwlClass")
    rdfs_class = URIRef("https://example.invalid/ontology#RdfsClass")
    obj_prop = URIRef("https://example.invalid/ontology#ObjProp")
    data_prop = URIRef("https://example.invalid/ontology#DataProp")
    ann_prop = URIRef("https://example.invalid/ontology#AnnProp")
    concept = URIRef("https://example.invalid/ontology#AConcept")
    subclass = URIRef("https://example.invalid/ontology#SubOnly")
    other = URIRef("https://example.invalid/ontology#Other")
    graph.add((owl_class, RDF.type, OWL.Class))
    graph.add((rdfs_class, RDF.type, RDFS.Class))
    graph.add((obj_prop, RDF.type, OWL.ObjectProperty))
    graph.add((data_prop, RDF.type, OWL.DatatypeProperty))
    graph.add((ann_prop, RDF.type, OWL.AnnotationProperty))
    graph.add((concept, RDF.type, SKOS.Concept))
    graph.add((subclass, RDFS.subClassOf, owl_class))
    graph.add((other, RDFS.label, URIRef("https://example.invalid/ontology#Label")))
    assert classify_term_kind(graph, str(owl_class)) == "class"
    assert classify_term_kind(graph, str(rdfs_class)) == "class"
    assert classify_term_kind(graph, str(obj_prop)) == "object_property"
    assert classify_term_kind(graph, str(data_prop)) == "datatype_property"
    assert classify_term_kind(graph, str(ann_prop)) == "annotation_property"
    assert classify_term_kind(graph, str(concept)) == "concept"
    assert classify_term_kind(graph, str(subclass)) == "class"
    assert classify_term_kind(graph, str(other)) == "other"


def test_kind_mismatch_does_not_emit_equivalent_class() -> None:
    """A shared local name of mixed term kind must not be mapped."""
    kg_terms = {
        term.local_name: term.term_kind
        for term in inventory_namespace_terms()
        if term.namespace == CANONICAL_ONTOLOGY_NAMESPACE
    }
    assert kg_terms.get("mentionedIn") != "class"
    assert (
        f"{CANONICAL_ONTOLOGY_NAMESPACE}mentionedIn",
        f"{DEPRECATED_PAGES_ONTOLOGY_NAMESPACE}mentionedIn",
    ) not in compatible_class_pairs()
