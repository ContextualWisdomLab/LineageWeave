"""Contract tests for the event-intelligence OWL/RDF profile."""

from pathlib import Path

from rdflib import Graph, Namespace, URIRef
from rdflib.namespace import OWL, RDF, RDFS

PROFILE = Path(__file__).parents[1] / "docs" / "ontology" / "event-intelligence-profile.ttl"
EI = Namespace("https://contextualwisdomlab.github.io/lineageweave/event-intelligence#")
PROV = Namespace("http://www.w3.org/ns/prov#")
TIME = Namespace("http://www.w3.org/2006/time#")
LW = Namespace("https://contextualwisdomlab.github.io/lineageweave/ontology#")


def load_profile() -> Graph:
    """Parse the committed profile into a fresh graph."""
    graph = Graph()
    graph.parse(PROFILE, format="turtle")
    return graph


def test_profile_declares_each_authority_without_conflating_roles() -> None:
    """TEPP, fast-mlsirm, the judge, and the graph remain distinct entities."""
    graph = load_profile()
    for class_iri in (
        EI.EventEpisode,
        EI.EventAssertion,
        EI.EvidenceBundle,
        EI.KnowledgeGraphProjection,
        EI.TemporalTopicArtifact,
        EI.PsychometricArtifact,
        EI.JudgeDecision,
        EI.EventIntelligenceDossier,
        EI.RelevanceMeasurement,
        EI.GroundedClaim,
    ):
        assert (class_iri, RDF.type, OWL.Class) in graph
        assert (class_iri, RDFS.subClassOf, PROV.Entity) in graph
    assert (EI.DossierGenerationActivity, RDF.type, OWL.Class) in graph
    assert (EI.DossierGenerationActivity, RDFS.subClassOf, PROV.Activity) in graph
    assert EI.TemporalTopicArtifact != EI.PsychometricArtifact
    assert EI.JudgeDecision != EI.PsychometricArtifact


def test_profile_keeps_generation_activity_separate_from_dossier_entity() -> None:
    """PROV usage and generation are owned by an activity, not the dossier entity."""
    graph = load_profile()
    assert (EI.usesEvidenceBundle, RDFS.subPropertyOf, PROV.used) in graph
    assert (EI.usesEvidenceBundle, RDFS.domain, EI.DossierGenerationActivity) in graph
    assert (EI.usesEvidenceBundle, RDFS.domain, EI.EventIntelligenceDossier) not in graph
    assert (EI.usesEventAssertion, RDFS.subPropertyOf, PROV.used) in graph
    assert (EI.generatesDossier, RDFS.subPropertyOf, PROV.generated) in graph
    assert (EI.generatesDossier, RDFS.range, EI.EventIntelligenceDossier) in graph


def test_profile_mediates_source_evidence_through_an_event_assertion() -> None:
    """A source supports an assertion without becoming a cause of the event."""
    graph = load_profile()
    assert (EI.assertsEvent, RDFS.domain, EI.EventAssertion) in graph
    assert (EI.assertsEvent, RDFS.range, EI.EventEpisode) in graph
    assert (EI.supportedBySource, RDFS.domain, EI.EventAssertion) in graph
    assert (EI.supportedBySource, RDFS.range, LW.Post) in graph
    assert (EI.supportedBySource, RDFS.subPropertyOf, PROV.wasDerivedFrom) in graph
    assert (EI.evidencesEvent, RDFS.subPropertyOf, PROV.influenced) not in graph


def test_profile_uses_owl_time_and_separates_transitions_from_retrospective_reports() -> None:
    """Event time is first-class and backward references are not transitions."""
    graph = load_profile()
    assert (EI.hasTemporalExtent, RDFS.range, TIME.Interval) in graph
    assert (EI.hasAssertionInstant, RDFS.range, TIME.Instant) in graph
    assert (EI.hasDocumentInstant, RDFS.range, TIME.Instant) in graph
    assert (EI.hasAvailableInstant, RDFS.range, TIME.Instant) in graph
    assert (EI.hasKnowledgeCutoffInstant, RDFS.range, TIME.Instant) in graph
    assert (EI.forwardTransition, RDF.type, OWL.ObjectProperty) in graph
    assert (EI.retrospectivelyReports, RDF.type, OWL.ObjectProperty) in graph
    assert EI.forwardTransition != EI.retrospectivelyReports
    assert (EI.retrospectivelyReports, RDFS.domain, LW.Post) in graph
    assert (EI.retrospectivelyReports, RDFS.range, EI.EventEpisode) in graph


def test_profile_preserves_provenance_and_exact_measurement_fields() -> None:
    """Dossier generation, source derivation, digests, methods, and intervals are explicit."""
    graph = load_profile()
    assert (EI.usesEvidenceBundle, RDFS.subPropertyOf, PROV.used) in graph
    assert (EI.generatesDossier, RDFS.subPropertyOf, PROV.generated) in graph
    assert (EI.supportedBySource, RDFS.subPropertyOf, PROV.wasDerivedFrom) in graph
    for property_iri in (
        EI.eventStart,
        EI.eventEnd,
        EI.assertionTime,
        EI.documentTime,
        EI.knowledgeCutoff,
        EI.availableTime,
        EI.methodCode,
        EI.methodVersion,
        EI.estimate,
        EI.uncertaintyLower,
        EI.uncertaintyUpper,
        EI.artifactDigestSha256,
        EI.verdictCode,
        EI.confidence,
    ):
        assert (property_iri, RDF.type, OWL.DatatypeProperty) in graph


def test_profile_is_versioned_imported_and_has_no_blank_semantic_terms() -> None:
    """Ontology identity, imports, and every declared semantic term are auditable."""
    graph = load_profile()
    ontology = URIRef("https://contextualwisdomlab.github.io/lineageweave/event-intelligence")
    assert (ontology, RDF.type, OWL.Ontology) in graph
    assert str(graph.value(ontology, OWL.versionInfo)) == "1.0.0"
    assert graph.value(ontology, OWL.versionIRI) == URIRef(
        "https://contextualwisdomlab.github.io/lineageweave/event-intelligence/1.0.0"
    )
    for imported_iri in (
        URIRef("https://contextualwisdomlab.github.io/lineageweave/ontology"),
        URIRef("http://www.w3.org/ns/prov-o"),
        URIRef("http://www.w3.org/2006/time"),
    ):
        assert (ontology, OWL.imports, imported_iri) in graph
    semantic_terms = set(graph.subjects(RDF.type, OWL.Class)) | set(
        graph.subjects(RDF.type, OWL.ObjectProperty)
    ) | set(graph.subjects(RDF.type, OWL.DatatypeProperty))
    assert semantic_terms
    for term in semantic_terms:
        assert graph.value(term, RDFS.label) is not None
