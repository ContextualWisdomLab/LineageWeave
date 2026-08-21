"""Contract tests for the published Event Intelligence SHACL shapes."""

from pathlib import Path

from rdflib import Graph, Namespace, URIRef
from rdflib.namespace import OWL, RDF

SHAPES = (
    Path(__file__).parents[1]
    / "docs"
    / "ontology"
    / "event-intelligence-profile.shacl.ttl"
)
EI = Namespace("https://contextualwisdomlab.github.io/lineageweave/event-intelligence#")
EIS = Namespace(
    "https://contextualwisdomlab.github.io/lineageweave/event-intelligence/shapes#"
)
SH = Namespace("http://www.w3.org/ns/shacl#")
TIME = Namespace("http://www.w3.org/2006/time#")


def load_shapes() -> Graph:
    """Parse the committed SHACL shapes into a fresh graph."""
    graph = Graph()
    graph.parse(SHAPES, format="turtle")
    return graph


def property_shape(graph: Graph, node_shape: URIRef, path: URIRef) -> URIRef:
    """Return the property shape for one required path."""
    return next(
        candidate
        for candidate in graph.objects(node_shape, SH.property)
        if graph.value(candidate, SH.path) == path
    )


def test_shapes_are_versioned_and_target_the_profile_classes() -> None:
    """The shapes graph is versioned and binds every semantic boundary class."""
    graph = load_shapes()
    ontology = URIRef(
        "https://contextualwisdomlab.github.io/lineageweave/event-intelligence/shapes"
    )
    assert (ontology, RDF.type, OWL.Ontology) in graph
    assert graph.value(ontology, OWL.versionIRI) == URIRef(
        "https://contextualwisdomlab.github.io/lineageweave/event-intelligence/shapes/1.0.0"
    )
    assert (
        EIS.DossierGenerationActivityShape,
        SH.targetClass,
        EI.DossierGenerationActivity,
    ) in graph
    assert (EIS.EventAssertionShape, SH.targetClass, EI.EventAssertion) in graph
    assert (EIS.EventEpisodeShape, SH.targetClass, EI.EventEpisode) in graph
    assert (EIS.EvidenceBundleShape, SH.targetClass, EI.EvidenceBundle) in graph


def test_shapes_enforce_activity_assertion_and_interval_boundaries() -> None:
    """Cardinality and class constraints keep PROV and OWL-Time roles distinct."""
    graph = load_shapes()
    uses_bundle = property_shape(
        graph,
        EIS.DossierGenerationActivityShape,
        EI.usesEvidenceBundle,
    )
    assert int(graph.value(uses_bundle, SH.minCount)) == 1
    assert int(graph.value(uses_bundle, SH.maxCount)) == 1
    asserts_event = property_shape(graph, EIS.EventAssertionShape, EI.assertsEvent)
    assert int(graph.value(asserts_event, SH.minCount)) == 1
    assert int(graph.value(asserts_event, SH.maxCount)) == 1
    temporal_extent = property_shape(
        graph,
        EIS.EventEpisodeShape,
        EI.hasTemporalExtent,
    )
    assert graph.value(temporal_extent, SH["class"]) == TIME.Interval
