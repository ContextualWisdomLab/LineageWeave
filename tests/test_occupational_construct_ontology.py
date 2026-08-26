"""Ontology checks for evidence-bound occupational constructs (ADR 0248)."""

from __future__ import annotations

from rdflib import BNode, Graph, Literal, URIRef
from rdflib.namespace import OWL, PROV, RDF, RDFS, XSD

from lineageweave.ontology import LW, load_ontology


def test_construct_families_are_distinct_from_worker_functions() -> None:
    """Construct families share a parent but never equate to FJA functions."""
    graph = load_ontology()
    families = {
        LW.CognitiveAbility,
        LW.WorkStyle,
        LW.WorkActivity,
        LW.AffectiveReaction,
        LW.PerformanceBehavior,
    }
    for family in families:
        assert (family, RDF.type, OWL.Class) in graph
        assert (family, RDFS.subClassOf, LW.OccupationalConstruct) in graph
        assert (family, OWL.equivalentClass, LW.WorkerFunction) not in graph
        assert (LW.WorkerFunction, OWL.equivalentClass, family) not in graph


def test_construct_assertion_has_fixed_reified_direction() -> None:
    """The schema fixes Post -> supports construct and never Person -> trait."""
    graph = load_ontology()
    assert (LW.supportsOccupationalConstruct, RDFS.domain, LW.Post) in graph
    assert (
        LW.supportsOccupationalConstruct,
        RDFS.range,
        LW.OccupationalConstruct,
    ) in graph
    restrictions = set(graph.objects(LW.OccupationalConstructAssertion, RDFS.subClassOf))
    assert any(
        (node, OWL.onProperty, RDF.predicate) in graph
        and (node, OWL.hasValue, LW.supportsOccupationalConstruct) in graph
        for node in restrictions
    )


def test_construct_assertion_shape_requires_evidence_and_provenance() -> None:
    """SHACL rejects a construct assertion without evidence and PROV metadata."""
    from pyshacl import validate

    shapes = Graph().parse("docs/ontology/lineageweave-kg-shapes.ttl", format="turtle")
    ontology = load_ontology()
    post = URIRef("https://example.test/post/synthetic")
    construct = URIRef("https://example.test/construct/synthetic")
    assertion = BNode()
    data = Graph()
    data += ontology
    data.add((post, RDF.type, LW.Post))
    data.add((post, LW.postTitle, Literal("Synthetic post")))
    data.add((post, LW.postBody, Literal("Synthetic body.")))
    data.add(
        (post, LW.createdAt, Literal("2026-08-27T00:00:00Z", datatype=XSD.dateTime))
    )
    data.add((construct, RDF.type, LW.CognitiveAbility))
    data.add((construct, RDF.type, LW.OccupationalConstruct))
    data.add((assertion, RDF.type, LW.OccupationalConstructAssertion))
    data.add((assertion, RDF.subject, post))
    data.add((assertion, RDF.predicate, LW.supportsOccupationalConstruct))
    data.add((assertion, RDF.object, construct))
    conforms, _, _ = validate(data, shacl_graph=shapes)
    assert not conforms

    data.add((assertion, LW.constructEvidence, Literal("Synthetic evidence.")))
    data.add((assertion, PROV.wasDerivedFrom, post))
    data.add(
        (
            assertion,
            PROV.generatedAtTime,
            Literal("2026-08-27T00:00:00Z", datatype=XSD.dateTime),
        )
    )
    conforms, _, report = validate(data, shacl_graph=shapes)
    assert conforms, report

    other_post = URIRef("https://example.test/post/other-synthetic")
    data.add((other_post, RDF.type, LW.Post))
    data.add((other_post, LW.postTitle, Literal("Other synthetic post")))
    data.add((other_post, LW.postBody, Literal("Other synthetic body.")))
    data.add(
        (
            other_post,
            LW.createdAt,
            Literal("2026-08-27T00:00:00Z", datatype=XSD.dateTime),
        )
    )
    data.remove((assertion, PROV.wasDerivedFrom, post))
    data.add((assertion, PROV.wasDerivedFrom, other_post))
    conforms, _, _ = validate(data, shacl_graph=shapes)
    assert not conforms
