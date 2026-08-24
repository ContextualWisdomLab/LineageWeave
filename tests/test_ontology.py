"""Real correctness check for docs/ontology/lineageweave-kg.ttl (ADR 0004):
the ontology's vocabulary must not silently drift from the
`common_lookup_value` rows the demo stack actually seeds. This is a
round-trip against `scripts/seed_demo_data.py`'s own committed SQL, not
a live database -- the two files are the actual pair that must stay in
sync, and this test fails the moment either one adds or renames a code
the other doesn't know about.
"""

from __future__ import annotations

import re
from pathlib import Path

from rdflib import Graph, URIRef
from rdflib.namespace import OWL, RDF, RDFS, SKOS, XSD

from lineageweave.knowledge_graph import (
    EDGE_AFFILIATION,
    EDGE_CO_MENTION,
    EDGE_MENTION,
    NODE_CORPORATE_ENTITY,
    NODE_PERSON,
    NODE_POST,
)
from lineageweave.ontology import (
    LW,
    all_declared_lookup_codes,
    iri_for_lookup_code,
    load_ontology,
    ontology_annotations,
    semantic_predicate_annotations,
)
from lineageweave.post_summary import SEMANTIC_RELATION_PREDICATES

_SEED_SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "seed_demo_data.py"
_SHAPES_PATH = Path(__file__).resolve().parents[1] / "docs" / "ontology" / "lineageweave-shapes.ttl"

# Several covered categories add lookup rows via their own migration
# SQL rather than literally embedded in seed_demo_data.py's own source
# text -- read alongside it below so the round-trip still sees them:
# 0012 (ADR 0006: prov_person/prov_organization), 0014 (ADR 0007:
# prov_team), 0016 (ADR 0009: node_team/edge_mention_team/
# edge_team_affiliation/edge_mention_organization).
_ADDITIONAL_LOOKUP_MIGRATION_PATHS = (
    Path(__file__).resolve().parents[1] / "migrations" / "0060_role_responsibility_agent_type.sql",
    Path(__file__).resolve().parents[1] / "migrations" / "0014_role_responsibility_team_actor_type.sql",
    Path(__file__).resolve().parents[1] / "migrations" / "0016_cross_post_actor_identity.sql",
    Path(__file__).resolve().parents[1] / "migrations" / "0108_post_summary_quantitative_observation.sql",
    Path(__file__).resolve().parents[1] / "migrations" / "0109_post_summary_source_fact.sql",
    Path(__file__).resolve().parents[1] / "migrations" / "0110_role_responsibility_software_agent.sql",
    Path(__file__).resolve().parents[1] / "migrations" / "0113_broad_source_fact_types.sql",
    Path(__file__).resolve().parents[1] / "migrations" / "0137_cross_post_customer_identity.sql",
)

# The categories this ontology covers (ADR 0004's scope). seed_demo_data.py
# also seeds categories this ontology does not model as KG node/edge
# predicates. Operational categories below are still modeled as SKOS
# concepts, so the full controlled vocabulary remains machine-checkable.
_ONTOLOGY_COVERED_CATEGORIES = frozenset(
    {
        "node_type",
        "edge_type",
        "entity_relationship_type",
        "person_side",
        "corporate_entity_level",
        "prov_agent_type",
        "post_visibility",
        "voc_type",
        "permission",
        "ticket_status",
        "measurement_type",
        "measurement_unit",
        "fact_type",
        "fact_assertion",
    }
)

_INSERT_TUPLE_PATTERN = re.compile(r"\('([a-z_]+)',\s*'([a-z_]+)'")


def _seeded_lookup_codes_for_covered_categories() -> set[str]:
    """Every `(lookup_category, lookup_code)` pair seed_demo_data.py's own
    SQL, plus the additional migrations' SQL, literally inserts, filtered
    to the categories this ontology covers. Parsed from source, not
    executed -- this is a static consistency check between committed
    files, not a live-database test.
    """
    source = _SEED_SCRIPT_PATH.read_text() + "".join(
        p.read_text() for p in _ADDITIONAL_LOOKUP_MIGRATION_PATHS
    )
    return {
        code
        for category, code in _INSERT_TUPLE_PATTERN.findall(source)
        if category in _ONTOLOGY_COVERED_CATEGORIES
    }


def test_ontology_parses_as_valid_turtle() -> None:
    graph = load_ontology()
    assert len(graph) > 0


def test_standards_profile_shapes_parse_as_valid_turtle() -> None:
    graph = Graph()
    graph.parse(_SHAPES_PATH, format="turtle")
    assert len(graph) > 0


def test_broad_profile_preserves_source_observation_and_clue_paths() -> None:
    graph = load_ontology()
    assert (LW.ObservationRecord, RDFS.subClassOf, URIRef("http://www.w3.org/ns/prov#Entity")) in graph
    assert (LW.EventObservation, RDFS.subClassOf, LW.ObservationRecord) in graph
    assert (LW.EvidenceClue, RDFS.subClassOf, URIRef("http://www.w3.org/ns/oa#Annotation")) in graph
    assert (LW.observesEvent, RDFS.range, LW.Event) in graph
    assert (LW.clueSource, RDFS.subPropertyOf, URIRef("http://www.w3.org/ns/prov#hadPrimarySource")) in graph
    assert (LW.hasEventTime, RDFS.subPropertyOf, URIRef("http://www.w3.org/2006/time#hasTime")) in graph
    assert (LW.factNormalizedDate, RDFS.subPropertyOf, URIRef("http://www.w3.org/2006/time#inXSDDate")) in graph


def test_profile_expands_actor_industrial_normative_and_quality_classes() -> None:
    graph = load_ontology()
    for term, parent in (
        (LW.RoleActorPerson, LW.Actor),
        (LW.RoleActorOrganization, LW.Actor),
        (LW.RoleActorTeam, LW.Actor),
        (LW.RoleActorSoftwareAgent, LW.Actor),
        (LW.IndustrialAsset, URIRef("http://www.w3.org/ns/prov#Entity")),
        (LW.IndustrialProcess, URIRef("http://www.w3.org/ns/prov#Activity")),
        (LW.NormativeStatement, URIRef("http://www.w3.org/ns/odrl/2/Rule")),
        (LW.QualityAssessment, LW.ObservationRecord),
        (LW.RiskStatement, LW.ObservationRecord),
    ):
        assert (term, RDFS.subClassOf, parent) in graph


def test_profile_declares_inverse_and_property_chain_for_graph_drawing() -> None:
    graph = load_ontology()
    assert (LW.hasCause, OWL.inverseOf, LW.causedBy) in graph
    assert (LW.hasConsequence, OWL.inverseOf, LW.consequenceOf) in graph
    assert (LW.hasNextStep, OWL.inverseOf, LW.nextStepOf) in graph
    assert graph.value(LW.affiliatedWith, OWL.propertyChainAxiom) is not None


def test_every_seeded_lookup_code_is_declared_in_the_ontology() -> None:
    seeded = _seeded_lookup_codes_for_covered_categories()
    declared = all_declared_lookup_codes()
    missing_from_ontology = seeded - declared
    assert not missing_from_ontology, (
        f"seed_demo_data.py seeds these codes with no matching ontology term: {missing_from_ontology}"
    )


def test_ontology_declares_no_lookup_code_the_seed_script_does_not_use() -> None:
    seeded = _seeded_lookup_codes_for_covered_categories()
    declared = all_declared_lookup_codes()
    stale_in_ontology = declared - seeded
    assert not stale_in_ontology, (
        f"lineageweave-kg.ttl declares codes seed_demo_data.py never inserts: {stale_in_ontology}"
    )


def test_knowledge_graph_lookup_constants_are_declared_in_the_ontology() -> None:
    """The codes knowledge_graph.py actually writes must stay in the
    ontology -- seed-script drift is not the only way the two can part.
    """
    declared = all_declared_lookup_codes()
    for code in (
        NODE_PERSON,
        NODE_CORPORATE_ENTITY,
        NODE_POST,
        EDGE_MENTION,
        EDGE_AFFILIATION,
        EDGE_CO_MENTION,
    ):
        assert code in declared, f"{code} is written by knowledge_graph.py but missing from lineageweave-kg.ttl"


def test_iri_for_lookup_code_resolves_a_real_term() -> None:
    assert iri_for_lookup_code("edge_mention") == str(LW.mentionedIn)
    assert iri_for_lookup_code("rel_voc") == str(LW.hasVocRelationship)


def test_iri_for_lookup_code_returns_none_for_an_undeclared_code() -> None:
    assert iri_for_lookup_code("not_a_real_lookup_code") is None


def test_ontology_annotations_carry_iri_and_label_for_a_node_type() -> None:
    assert ontology_annotations("node_person") == {
        "ontology_iri": str(LW.Person),
        "ontology_label": "Person",
    }
    assert ontology_annotations("node_post")["ontology_label"] == "Post"
    assert ontology_annotations("node_corporate_entity")["ontology_label"] == "Corporate entity"


def test_ontology_annotations_are_empty_for_an_undeclared_code() -> None:
    assert ontology_annotations("not_a_real_lookup_code") == {}
    assert ontology_annotations("open") == {
        "ontology_iri": str(LW.OpenTicketStatus),
        "ontology_label": "Open",
    }


def test_operational_controlled_vocabulary_uses_skos_concepts() -> None:
    """Visibility, VOC, permission, and ticket state are semantic concepts,
    not untyped strings or invented graph edge predicates.
    """
    graph = load_ontology()
    for code, term in (
        ("public", LW.PublicVisibility),
        ("voc", LW.VoiceOfCustomer),
        ("post_read", LW.ReadPostsPermission),
        ("open", LW.OpenTicketStatus),
    ):
        assert iri_for_lookup_code(code) == str(term)
        assert (term, RDF.type, SKOS.Concept) in graph
        assert (term, SKOS.inScheme, None) in graph

    assert (LW.hasPostVisibility, RDFS.domain, LW.Post) in graph
    assert (LW.hasPostVisibility, RDFS.range, SKOS.Concept) in graph
    assert (LW.hasPermission, RDFS.domain, LW.AccessRole) in graph
    assert (LW.hasTicketStatus, RDFS.domain, LW.IssueTicket) in graph


def test_mentioned_in_property_matches_canonical_edge_direction() -> None:
    """`mentionedIn` goes Person -> Post, matching stored KG triples."""
    graph = load_ontology()
    assert (LW.mentionedIn, RDFS.domain, LW.Person) in graph
    assert (LW.mentionedIn, RDFS.range, LW.Post) in graph
    assert (LW.mentions, OWL.inverseOf, LW.mentionedIn) in graph


def test_prov_agent_type_terms_resolve_and_subclass_real_prov_o() -> None:
    """Beyond the generic round-trip above: the two prov_agent_type terms
    must actually subclass the real external W3C PROV-O classes, not
    just carry a matching :lookupCode -- the whole point of grounding
    this in a standard ontology is that :RoleActorPerson really is a
    prov:Person, not a same-named local invention.
    """
    from rdflib import URIRef
    from rdflib.namespace import Namespace

    prov = Namespace("http://www.w3.org/ns/prov#")
    graph = load_ontology()
    assert iri_for_lookup_code("prov_person") == str(LW.RoleActorPerson)
    assert iri_for_lookup_code("prov_organization") == str(LW.RoleActorOrganization)
    assert (LW.RoleActorPerson, RDFS.subClassOf, URIRef(prov.Person)) in graph
    assert (LW.RoleActorOrganization, RDFS.subClassOf, URIRef(prov.Organization)) in graph
    assert iri_for_lookup_code("prov_software_agent") == str(LW.RoleActorSoftwareAgent)
    assert (LW.RoleActorSoftwareAgent, RDFS.subClassOf, URIRef(prov.SoftwareAgent)) in graph
    assert (LW.RoleActorPerson, RDFS.subClassOf, LW.RoleActorAgent) in graph


def test_prov_team_type_resolves_and_subclasses_real_org_ontology() -> None:
    """ADR 0007: a team actor is grounded in the real external W3C
    Organization Ontology's org:OrganizationalUnit, the meso-level
    sub-organization concept PROV-O itself has no equivalent for.
    """
    from rdflib import URIRef
    from rdflib.namespace import Namespace

    org = Namespace("http://www.w3.org/ns/org#")
    graph = load_ontology()
    assert iri_for_lookup_code("prov_team") == str(LW.RoleActorTeam)
    assert (LW.RoleActorTeam, RDFS.subClassOf, URIRef(org.OrganizationalUnit)) in graph


def test_corporate_entity_level_hierarchy_is_broadest_first() -> None:
    """Group is broader than Company is broader than Plant -- the
    Acme Group -> Acme Electronics Korea -> plant direction the
    product brief describes."""
    graph = load_ontology()
    assert (LW.CompanyLevel, SKOS.broader, LW.GroupLevel) in graph
    assert (LW.PlantLevel, SKOS.broader, LW.CompanyLevel) in graph
    assert (LW.GroupLevel, SKOS.broader, LW.CompanyLevel) not in graph


def test_actor_mentions_follow_stored_edge_direction() -> None:
    """Ontology domain/range matches Team/Organization -> Post storage."""
    graph = load_ontology()
    assert (LW.mentionsTeam, RDFS.domain, LW.Team) in graph
    assert (LW.mentionsTeam, RDFS.range, LW.Post) in graph
    assert (LW.mentionsOrganization, RDFS.domain, LW.CorporateEntity) in graph
    assert (LW.mentionsOrganization, RDFS.range, LW.Post) in graph
    assert (LW.observedCustomerIdentityIn, RDFS.domain, LW.CorporateEntity) in graph
    assert (LW.observedCustomerIdentityIn, RDFS.range, LW.Post) in graph


def test_semantic_project_terms_preserve_post_evidence_and_confidence() -> None:
    """ADR 0036's project vocabulary must remain machine-checkable."""
    graph = load_ontology()
    ontology = URIRef("https://contextualwisdomlab.github.io/lineageweave/ontology")
    assert "OWL 2 Full" in str(graph.value(ontology, RDFS.comment))
    assert (LW.Project, RDF.type, OWL.Class) in graph
    assert (LW.ProjectMention, RDF.type, OWL.Class) in graph
    restrictions = set(graph.objects(LW.ProjectMention, RDFS.subClassOf))
    assert any(
        (node, OWL.onProperty, RDF.subject) in graph
        and (node, OWL.allValuesFrom, LW.Post) in graph
        for node in restrictions
    )
    assert any(
        (node, OWL.onProperty, RDF.predicate) in graph
        and (node, OWL.hasValue, LW.mentionsProject) in graph
        for node in restrictions
    )
    assert any(
        (node, OWL.onProperty, RDF.object) in graph
        and (node, OWL.allValuesFrom, LW.Project) in graph
        for node in restrictions
    )
    assert (LW.mentionsProject, RDFS.domain, LW.Post) in graph
    assert (LW.mentionsProject, RDFS.range, LW.Project) in graph
    assert (LW.projectEvidence, RDFS.domain, LW.ProjectMention) in graph
    assert (LW.projectEvidence, RDFS.range, XSD.string) in graph


def test_standard_backbone_and_semantic_verbs_are_drawable() -> None:
    from rdflib.namespace import Namespace

    prov = Namespace("http://www.w3.org/ns/prov#")
    graph = load_ontology()
    assert (LW.Post, RDFS.subClassOf, prov.Entity) in graph
    assert (LW.Person, RDFS.subClassOf, prov.Person) in graph
    assert (LW.CorporateEntity, RDFS.subClassOf, prov.Organization) in graph
    assert (LW.hasRoleResponsibility, RDFS.range, LW.RoleResponsibility) in graph
    assert (LW.roleResponsibilityOf, OWL.inverseOf, LW.hasRoleResponsibility) in graph
    assert (LW.roleResponsibilityOf, RDFS.subPropertyOf, prov.wasDerivedFrom) in graph
    assert (LW.hasSemanticAssertion, RDFS.range, LW.SemanticAssertion) in graph
    assert semantic_predicate_annotations("prov_was_influenced_by") == {
        "ontology_iri": "http://www.w3.org/ns/prov#wasInfluencedBy",
        "ontology_label": "Was influenced by",
    }
    assert semantic_predicate_annotations("lw_has_cause")["ontology_iri"] == str(LW.hasCause)
    assert all(semantic_predicate_annotations(code) for code in SEMANTIC_RELATION_PREDICATES)


def test_temporal_profile_subclasses_owl_time_and_uses_canonical_before_direction() -> None:
    """Temporal order is earlier time to later time, not a private successor verb."""
    from rdflib.namespace import Namespace

    time = Namespace("http://www.w3.org/2006/time#")
    graph = load_ontology()
    assert (LW.TemporalEntity, RDFS.subClassOf, time.TemporalEntity) in graph
    assert semantic_predicate_annotations("time_before") == {
        "ontology_iri": str(time.before),
        "ontology_label": "Before",
    }


def test_property_chains_capture_only_explicit_contextual_inference() -> None:
    from rdflib import URIRef
    from rdflib.namespace import Namespace

    owl = Namespace("http://www.w3.org/2002/07/owl#")
    graph = load_ontology()
    for property_iri, expected in (
        (LW.hasAffiliatedCorporateContext, [LW.mentions, LW.affiliatedWith]),
        (LW.hasTeamCorporateContext, [LW.postMentionsTeam, LW.teamAffiliatedWith]),
        (LW.mentionsProject, [LW.hasProjectMention, LW.projectMentionFor]),
    ):
        chain = graph.value(property_iri, URIRef(owl.propertyChainAxiom))
        assert list(graph.items(chain)) == expected


def test_shacl_shapes_norm_relation_evidence_and_confidence() -> None:
    from rdflib.namespace import Namespace

    sh = Namespace("http://www.w3.org/ns/shacl#")
    graph = load_ontology()
    assert (LW.SemanticRelationshipShape, RDF.type, sh.NodeShape) in graph
    assert (LW.SemanticRelationshipShape, sh.targetClass, LW.SemanticRelationship) in graph
    assert (LW.ProjectMentionShape, sh.targetClass, LW.ProjectMention) in graph
    assert (LW.semanticConfidence, RDFS.range, XSD.decimal) in graph
    assert (LW.semanticConfidence, RDFS.domain, LW.ProjectMention) in graph
