"""Semantic-profile tests for project lifecycle history."""

from pathlib import Path

from rdflib import Graph, Namespace, RDF, RDFS
from rdflib.namespace import OWL

_ROOT = Path(__file__).resolve().parents[1]
PROFILE = _ROOT / "docs/ontology/project-history-profile.ttl"
PH = Namespace("https://contextualwisdomlab.github.io/lineageweave/project-history#")
TIME = Namespace("http://www.w3.org/2006/time#")
PROV = Namespace("http://www.w3.org/ns/prov#")


def test_project_history_profile_parses_and_separates_association_from_causality() -> None:
    graph = Graph().parse(PROFILE, format="turtle")
    assert (PH.ProjectHistoryEvent, RDFS.subClassOf, TIME.TemporalEntity) in graph
    assert (PH.ResponsibilityAssignment, RDFS.subClassOf, TIME.ProperInterval) in graph
    assert (PH.ResponsibilityAssignment, RDFS.subClassOf, PROV.Association) in graph
    assert (PH.hasProjectEvidence, RDFS.subPropertyOf, PROV.used) in graph
    assert (PH.followsProjectEvent, RDFS.subPropertyOf, TIME.after) in graph
    assert (PH.projectRelatedTo, RDF.type, OWL.SymmetricProperty) in graph
    assert (PH.projectRelatedTo, RDFS.subPropertyOf, PH.causes) not in graph
