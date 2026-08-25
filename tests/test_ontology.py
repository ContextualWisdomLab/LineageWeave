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

from lineageweave.knowledge_graph import (
    EDGE_AFFILIATION,
    EDGE_CO_MENTION,
    EDGE_MENTION,
    NODE_CORPORATE_ENTITY,
    NODE_PERSON,
    NODE_POST,
)
from lineageweave.ontology import (
    LOOKUP_CODE,
    LW,
    all_declared_lookup_codes,
    iri_for_lookup_code,
    load_ontology,
    ontology_annotations,
)
from rdflib import URIRef
from rdflib.namespace import OWL, RDF, RDFS, SKOS, XSD

_SEED_SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "seed_demo_data.py"

# Several covered categories add lookup rows via their own migration
# SQL rather than literally embedded in seed_demo_data.py's own source
# text -- read alongside it below so the round-trip still sees them:
# 0012 (ADR 0006: prov_person/prov_organization), 0014 (ADR 0007:
# prov_team), 0016 (ADR 0009: node_team/edge_mention_team/
# edge_team_affiliation/edge_mention_organization), and 0042 (ADR 0205:
# the five governed voc_type post-type codes).
_ADDITIONAL_LOOKUP_MIGRATION_PATHS = (
    Path(__file__).resolve().parents[1] / "migrations" / "0060_role_responsibility_agent_type.sql",
    Path(__file__).resolve().parents[1] / "migrations" / "0014_role_responsibility_team_actor_type.sql",
    Path(__file__).resolve().parents[1] / "migrations" / "0016_cross_post_actor_identity.sql",
    Path(__file__).resolve().parents[1] / "migrations" / "0042_voc_type_vocabulary.sql",
)

# The categories this ontology covers (ADR 0004's scope, extended by
# ADR 0205 with voc_type's post-type scheme). seed_demo_data.py also
# seeds categories this ontology deliberately does not model yet
# (post_visibility, permission, ticket_status) -- those are real,
# expected gaps, not a test bug.
_ONTOLOGY_COVERED_CATEGORIES = frozenset(
    {
        "node_type",
        "edge_type",
        "entity_relationship_type",
        "person_side",
        "corporate_entity_level",
        "prov_agent_type",
        "voc_type",
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
    # `open` is a real ticket_status lookup code this ontology
    # deliberately does not cover -- missing, not a fake label.
    assert ontology_annotations("open") == {}


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


def test_semantic_project_terms_preserve_post_evidence_and_confidence() -> None:
    """ADR 0036's project vocabulary must remain machine-checkable."""
    graph = load_ontology()
    ontology = URIRef("https://contextualwisdomlab.github.io/LineageWeave/ontology")
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
    assert (LW.semanticConfidence, RDFS.range, XSD.decimal) in graph
    assert (LW.semanticConfidence, RDFS.domain, LW.ProjectMention) in graph


def test_ontology_iri_is_repository_case_canonical() -> None:
    """ADR 0205: the ontology IRI and every term IRI use the
    repository-case namespace -- the exact path GitHub Pages serves --
    and the lowercase spelling never appears as a minted subject.
    """
    canonical = "https://contextualwisdomlab.github.io/LineageWeave/ontology#"
    lowercase = "https://contextualwisdomlab.github.io/lineageweave/ontology#"
    graph = load_ontology()
    assert (
        URIRef("https://contextualwisdomlab.github.io/LineageWeave/ontology"),
        RDF.type,
        OWL.Ontology,
    ) in graph
    assert str(LW) == canonical
    for subject in set(graph.subjects()):
        if isinstance(subject, URIRef):
            assert not str(subject).startswith(lowercase), str(subject)


def test_person_sides_are_declared_disjoint() -> None:
    """ADR 0205 decision 9: a person side is our-side or counterparty,
    never both -- stated with owl:disjointWith so reasoners refuse a row
    that projects both codes.
    """
    graph = load_ontology()
    assert (LW.OurSidePerson, OWL.disjointWith, LW.CounterpartyPerson) in graph


def test_has_affiliate_is_the_stored_affiliation_inverse() -> None:
    """Bidirectional affiliation queries resolve through :hasAffiliate;
    like :mentions it carries no lookup code so one code keeps naming
    exactly one stored property.
    """
    graph = load_ontology()
    assert (LW.hasAffiliate, OWL.inverseOf, LW.affiliatedWith) in graph
    assert (LW.hasAffiliate, RDFS.domain, LW.CorporateEntity) in graph
    assert (LW.hasAffiliate, RDFS.range, LW.Person) in graph
    declared_codes = all_declared_lookup_codes()
    for value in graph.objects(LW.hasAffiliate, LOOKUP_CODE):
        raise AssertionError(f":hasAffiliate must stay un-coded; found {value}")
    assert "edge_affiliation" in declared_codes


def test_node_attribute_datatype_properties_project_real_columns() -> None:
    """ADR 0205 decision 7: attribute properties exist exactly for real
    schema columns, with correct domains/ranges, and no property is
    invented for a column that does not exist.
    """
    graph = load_ontology()
    expected = {
        (LW.postTitle, LW.Post, XSD.string),
        (LW.postBody, LW.Post, XSD.string),
        (LW.eventOccurredAt, LW.Post, XSD.dateTime),
        (LW.personName, LW.Person, XSD.string),
        (LW.lastKnownJobTitle, LW.Person, XSD.string),
        (LW.entityName, LW.CorporateEntity, XSD.string),
        (LW.entityCode, LW.CorporateEntity, XSD.string),
    }
    for prop, domain, datatype_range in expected:
        assert (prop, RDF.type, OWL.DatatypeProperty) in graph, str(prop)
        assert (prop, RDFS.domain, domain) in graph, str(prop)
        assert (prop, RDFS.range, datatype_range) in graph, str(prop)


def test_shared_timestamps_declare_no_domain_to_avoid_multi_domain_entailment() -> None:
    """Two rdfs:domain statements would entail every subject belongs to
    both classes -- the trap the cross-post edges already avoid. Shared
    timestamps therefore carry no domain; SHACL pins them per class.
    """
    graph = load_ontology()
    for prop in (LW.createdAt, LW.updatedAt):
        assert (prop, RDF.type, OWL.DatatypeProperty) in graph
        assert (prop, RDFS.range, XSD.dateTime) in graph
        domains = list(graph.objects(prop, RDFS.domain))
        assert domains == [], f"{prop} unexpectedly declares domains: {domains}"


def test_post_type_scheme_covers_the_governed_voc_vocabulary() -> None:
    """ADR 0205 decision 8: the five seeded voc_type codes become SKOS
    concepts; vos exists only as rel_vos and must NOT appear here.
    """
    graph = load_ontology()
    scheme_members = {
        subject for subject in graph.subjects(SKOS.inScheme, LW.postTypeScheme)
    }
    expected = {
        (LW.voiceOfCustomerType, "voc"),
        (LW.voiceOfCustomersCustomerType, "vocc"),
        (LW.voiceOfCompetitorType, "voco"),
        (LW.voiceOfMarketType, "vom"),
        (LW.voiceOfPartnerType, "vop"),
    }
    for concept, code in expected:
        assert concept in scheme_members, str(concept)
        assert iri_for_lookup_code(code) == str(concept)
    assert len(scheme_members) == len(expected)
    seeded = _seeded_lookup_codes_for_covered_categories()
    assert {"voc", "vocc", "voco", "vom", "vop"} <= seeded
    assert iri_for_lookup_code("vos") is None  # relationship type only
