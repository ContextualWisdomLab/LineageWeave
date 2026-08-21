"""Interoperability contracts for the core LineageWeave ontology and shapes."""

from pathlib import Path

from rdflib import Graph, Namespace, URIRef
from rdflib.namespace import OWL, RDF, RDFS, SKOS

ONTOLOGY = Path(__file__).parents[1] / "docs" / "ontology" / "lineageweave-kg.ttl"
SHAPES = (
    Path(__file__).parents[1]
    / "docs"
    / "ontology"
    / "lineageweave-kg.shacl.ttl"
)
LW = Namespace("https://contextualwisdomlab.github.io/lineageweave/ontology#")
LWS = Namespace("https://contextualwisdomlab.github.io/lineageweave/ontology/shapes#")
ORG = Namespace("http://www.w3.org/ns/org#")
SH = Namespace("http://www.w3.org/ns/shacl#")


def load_ontology_graph() -> Graph:
    """Parse the committed core ontology into a fresh graph."""
    graph = Graph()
    graph.parse(ONTOLOGY, format="turtle")
    return graph


def load_shapes_graph() -> Graph:
    """Parse the committed SHACL graph after asserting it is published."""
    assert SHAPES.exists(), "the core ontology must publish a SHACL shapes graph"
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


def test_real_organizations_are_not_skos_classification_concepts() -> None:
    """Corporate entities use W3C ORG while SKOS owns only level concepts."""
    graph = load_ontology_graph()
    assert (LW.CorporateEntity, RDFS.subClassOf, ORG.Organization) in graph
    assert (LW.CorporateEntity, RDFS.subClassOf, SKOS.Concept) not in graph
    assert (LW.CorporateEntityLevel, RDFS.subClassOf, SKOS.Concept) in graph
    assert (LW.GroupLevel, RDF.type, LW.CorporateEntityLevel) in graph
    assert (LW.CompanyLevel, RDF.type, LW.CorporateEntityLevel) in graph
    assert (LW.PlantLevel, RDF.type, LW.CorporateEntityLevel) in graph
    assert (LW.hasEntityLevel, RDFS.domain, LW.CorporateEntity) in graph
    assert (LW.hasEntityLevel, RDFS.range, LW.CorporateEntityLevel) in graph


def test_organizational_containment_reuses_w3c_org_relations() -> None:
    """Parent corporations and teams specialize the correct ORG relations."""
    graph = load_ontology_graph()
    assert (LW.subOrganizationOf, RDFS.subPropertyOf, ORG.subOrganizationOf) in graph
    assert (LW.hasSubOrganization, OWL.inverseOf, LW.subOrganizationOf) in graph
    assert (LW.teamAffiliatedWith, RDFS.subPropertyOf, ORG.unitOf) in graph


def test_core_ontology_has_stable_version_and_import_metadata() -> None:
    """Consumers can bind the exact profile without network dereferencing."""
    graph = load_ontology_graph()
    ontology = URIRef("https://contextualwisdomlab.github.io/lineageweave/ontology")
    assert graph.value(ontology, OWL.versionIRI) == URIRef(
        "https://contextualwisdomlab.github.io/lineageweave/ontology/1.0.0"
    )
    assert str(graph.value(ontology, OWL.versionInfo)) == "1.0.0"
    for imported_iri in (
        URIRef("http://www.w3.org/ns/org"),
        URIRef("http://www.w3.org/ns/prov-o"),
        URIRef("http://www.w3.org/2004/02/skos/core"),
    ):
        assert (ontology, OWL.imports, imported_iri) in graph


def test_core_shapes_enforce_level_and_parent_boundaries() -> None:
    """SHACL cardinalities complement the ontology's open-world semantics."""
    graph = load_shapes_graph()
    assert (LWS.CorporateEntityShape, SH.targetClass, LW.CorporateEntity) in graph
    assert (LWS.TeamShape, SH.targetClass, LW.Team) in graph
    entity_level = property_shape(graph, LWS.CorporateEntityShape, LW.hasEntityLevel)
    assert int(graph.value(entity_level, SH.minCount)) == 1
    assert int(graph.value(entity_level, SH.maxCount)) == 1
    parent = property_shape(graph, LWS.CorporateEntityShape, LW.subOrganizationOf)
    assert int(graph.value(parent, SH.maxCount)) == 1
    team_owner = property_shape(graph, LWS.TeamShape, LW.teamAffiliatedWith)
    assert int(graph.value(team_owner, SH.minCount)) == 1
    assert int(graph.value(team_owner, SH.maxCount)) == 1
