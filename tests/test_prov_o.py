from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import sys

import pytest
from rdflib import Graph, Literal, Namespace, URIRef
from rdflib.namespace import RDF, XSD

from lineageweave.prov_o import (
    PROV,
    PROV_CLASSES,
    PROV_QUALIFICATIONS,
    PROV_RELATIONS,
    PROV_RECOMMENDED_INVERSES,
    ProvAssertion,
    ProvGraph,
    ProvLiteral,
    ProvValidationError,
    class_code,
    relation_code,
)

EXPECTED_CLASS_NAMES = {
    "Entity", "Activity", "Agent", "Collection", "EmptyCollection", "Bundle",
    "Person", "SoftwareAgent", "Organization", "Location", "Influence",
    "EntityInfluence", "Usage", "Start", "End", "Derivation", "PrimarySource",
    "Quotation", "Revision", "ActivityInfluence", "Generation", "Communication",
    "Invalidation", "AgentInfluence", "Attribution", "Association", "Plan",
    "Delegation", "InstantaneousEvent", "Role",
}

EXPECTED_RELATION_NAMES = {
    "wasGeneratedBy", "wasDerivedFrom", "wasAttributedTo", "startedAtTime", "used",
    "wasInformedBy", "endedAtTime", "wasAssociatedWith", "actedOnBehalfOf",
    "alternateOf", "specializationOf", "generatedAtTime", "hadPrimarySource", "value",
    "wasQuotedFrom", "wasRevisionOf", "invalidatedAtTime", "wasInvalidatedBy",
    "hadMember", "wasStartedBy", "wasEndedBy", "invalidated", "influenced",
    "atLocation", "generated", "wasInfluencedBy", "qualifiedInfluence",
    "qualifiedGeneration", "qualifiedDerivation", "qualifiedPrimarySource",
    "qualifiedQuotation", "qualifiedRevision", "qualifiedAttribution",
    "qualifiedInvalidation", "qualifiedStart", "qualifiedUsage",
    "qualifiedCommunication", "qualifiedAssociation", "qualifiedEnd",
    "qualifiedDelegation", "influencer", "entity", "hadUsage", "hadGeneration",
    "activity", "agent", "hadPlan", "hadActivity", "atTime", "hadRole",
}

EXPECTED_DATATYPE_RELATIONS = {
    "startedAtTime", "endedAtTime", "generatedAtTime", "invalidatedAtTime", "value", "atTime"
}

EXPECTED_QUALIFICATIONS = {
    "wasGeneratedBy": ("qualifiedGeneration", "Generation", "activity"),
    "wasDerivedFrom": ("qualifiedDerivation", "Derivation", "entity"),
    "wasAttributedTo": ("qualifiedAttribution", "Attribution", "agent"),
    "used": ("qualifiedUsage", "Usage", "entity"),
    "wasInformedBy": ("qualifiedCommunication", "Communication", "activity"),
    "wasAssociatedWith": ("qualifiedAssociation", "Association", "agent"),
    "actedOnBehalfOf": ("qualifiedDelegation", "Delegation", "agent"),
    "wasInfluencedBy": ("qualifiedInfluence", "Influence", "influencer"),
    "hadPrimarySource": ("qualifiedPrimarySource", "PrimarySource", "entity"),
    "wasQuotedFrom": ("qualifiedQuotation", "Quotation", "entity"),
    "wasRevisionOf": ("qualifiedRevision", "Revision", "entity"),
    "wasInvalidatedBy": ("qualifiedInvalidation", "Invalidation", "activity"),
    "wasStartedBy": ("qualifiedStart", "Start", "entity"),
    "wasEndedBy": ("qualifiedEnd", "End", "entity"),
}


def test_registry_contains_every_normative_prov_o_class_and_relation() -> None:
    assert set(PROV_CLASSES) == EXPECTED_CLASS_NAMES
    assert set(PROV_RELATIONS) == EXPECTED_RELATION_NAMES
    assert len(PROV_CLASSES) == 30
    assert len(PROV_RELATIONS) == 50


def test_registry_distinguishes_all_six_datatype_properties() -> None:
    actual = {name for name, spec in PROV_RELATIONS.items() if spec.property_kind == "datatype"}
    assert actual == EXPECTED_DATATYPE_RELATIONS
    assert {name for name, spec in PROV_RELATIONS.items() if spec.property_kind == "object"} == (
        EXPECTED_RELATION_NAMES - EXPECTED_DATATYPE_RELATIONS
    )


def test_qualification_table_matches_both_normative_tables() -> None:
    actual = {
        item.unqualified_relation: (
            item.qualification_relation,
            item.influence_class,
            item.influencer_relation,
        )
        for item in PROV_QUALIFICATIONS
    }
    assert actual == EXPECTED_QUALIFICATIONS


def test_every_object_property_has_the_appendix_b_inverse_name() -> None:
    object_properties = {
        name for name, spec in PROV_RELATIONS.items() if spec.property_kind == "object"
    }
    assert set(PROV_RECOMMENDED_INVERSES) == object_properties
    assert PROV_RECOMMENDED_INVERSES["actedOnBehalfOf"].inverse_local_name == "hadDelegate"
    assert PROV_RECOMMENDED_INVERSES["wasDerivedFrom"].inverse_local_name == "hadDerivation"
    assert PROV_RECOMMENDED_INVERSES["specializationOf"].inverse_local_name == "generalizationOf"
    assert PROV_RECOMMENDED_INVERSES["wasGeneratedBy"].inverse_local_name == "generated"
    assert PROV_RECOMMENDED_INVERSES["alternateOf"].inverse_local_name == "alternateOf"


def test_codes_are_stable_two_word_snake_case() -> None:
    assert class_code("Entity") == "prov_entity"
    assert class_code("InstantaneousEvent") == "prov_instantaneous_event"
    assert relation_code("wasGeneratedBy") == "prov_was_generated_by"
    assert relation_code("qualifiedPrimarySource") == "prov_qualified_primary_source"
    for name in PROV_CLASSES:
        assert class_code(name).startswith("prov_") and "_" in class_code(name)
    for name in PROV_RELATIONS:
        assert relation_code(name).startswith("prov_") and "_" in relation_code(name)


def _graph_with_core_resources() -> ProvGraph:
    graph = ProvGraph()
    graph.add_resource("urn:entity:input", "Entity")
    graph.add_resource("urn:entity:output", "Entity")
    graph.add_resource("urn:activity:transform", "Activity")
    graph.add_resource("urn:agent:operator", "Person")
    graph.add_resource("urn:agent:principal", "Organization")
    graph.add_resource("urn:location:lab", "Location")
    graph.add_resource("urn:plan:procedure", "Plan")
    graph.add_resource("urn:role:reviewer", "Role")
    return graph


def test_graph_rejects_wrong_object_kind_and_wrong_domain() -> None:
    graph = _graph_with_core_resources()
    with pytest.raises(ProvValidationError, match="requires a resource object"):
        graph.add_assertion("urn:activity:transform", "used", ProvLiteral("not-a-resource"))
    with pytest.raises(ProvValidationError, match="requires a literal object"):
        graph.add_assertion("urn:activity:transform", "startedAtTime", "urn:entity:input")
    with pytest.raises(ProvValidationError, match="subject.*Entity"):
        graph.add_assertion("urn:agent:operator", "wasDerivedFrom", "urn:entity:input")


def test_subclass_membership_satisfies_agent_domain() -> None:
    graph = _graph_with_core_resources()
    graph.add_assertion("urn:agent:operator", "actedOnBehalfOf", "urn:agent:principal")
    assert ProvAssertion.resource(
        "urn:agent:operator", "actedOnBehalfOf", "urn:agent:principal"
    ) in graph.explicit_assertions


@pytest.mark.parametrize(
    ("unqualified", "qualified", "influence_class", "influencer_relation", "subject", "object_iri"),
    [
        ("wasGeneratedBy", "qualifiedGeneration", "Generation", "activity", "urn:entity:output", "urn:activity:transform"),
        ("wasDerivedFrom", "qualifiedDerivation", "Derivation", "entity", "urn:entity:output", "urn:entity:input"),
        ("wasAttributedTo", "qualifiedAttribution", "Attribution", "agent", "urn:entity:output", "urn:agent:operator"),
        ("used", "qualifiedUsage", "Usage", "entity", "urn:activity:transform", "urn:entity:input"),
        ("wasInformedBy", "qualifiedCommunication", "Communication", "activity", "urn:activity:transform", "urn:activity:source"),
        ("wasAssociatedWith", "qualifiedAssociation", "Association", "agent", "urn:activity:transform", "urn:agent:operator"),
        ("actedOnBehalfOf", "qualifiedDelegation", "Delegation", "agent", "urn:agent:operator", "urn:agent:principal"),
        ("wasInfluencedBy", "qualifiedInfluence", "Influence", "influencer", "urn:entity:output", "urn:entity:input"),
        ("hadPrimarySource", "qualifiedPrimarySource", "PrimarySource", "entity", "urn:entity:output", "urn:entity:input"),
        ("wasQuotedFrom", "qualifiedQuotation", "Quotation", "entity", "urn:entity:output", "urn:entity:input"),
        ("wasRevisionOf", "qualifiedRevision", "Revision", "entity", "urn:entity:output", "urn:entity:input"),
        ("wasInvalidatedBy", "qualifiedInvalidation", "Invalidation", "activity", "urn:entity:output", "urn:activity:transform"),
        ("wasStartedBy", "qualifiedStart", "Start", "entity", "urn:activity:transform", "urn:entity:input"),
        ("wasEndedBy", "qualifiedEnd", "End", "entity", "urn:activity:transform", "urn:entity:output"),
    ],
)
def test_each_qualified_form_implies_its_unqualified_form(
    unqualified: str,
    qualified: str,
    influence_class: str,
    influencer_relation: str,
    subject: str,
    object_iri: str,
) -> None:
    graph = _graph_with_core_resources()
    graph.add_resource("urn:activity:source", "Activity")
    graph.add_resource("urn:influence:q", influence_class)
    graph.add_assertion(subject, qualified, "urn:influence:q")
    graph.add_assertion("urn:influence:q", influencer_relation, object_iri)
    assert ProvAssertion.resource(subject, unqualified, object_iri) in graph.materialized_assertions()


def test_specific_derivation_implies_general_derivation_and_influence() -> None:
    graph = _graph_with_core_resources()
    graph.add_assertion("urn:entity:output", "wasQuotedFrom", "urn:entity:input")
    materialized = graph.materialized_assertions()
    assert ProvAssertion.resource("urn:entity:output", "wasDerivedFrom", "urn:entity:input") in materialized
    assert ProvAssertion.resource("urn:entity:output", "wasInfluencedBy", "urn:entity:input") in materialized


def test_defined_inverse_and_symmetric_properties_are_materialized() -> None:
    graph = _graph_with_core_resources()
    graph.add_assertion("urn:entity:output", "wasGeneratedBy", "urn:activity:transform")
    graph.add_assertion("urn:entity:output", "alternateOf", "urn:entity:input")
    materialized = graph.materialized_assertions()
    assert ProvAssertion.resource("urn:activity:transform", "generated", "urn:entity:output") in materialized
    assert ProvAssertion.resource("urn:entity:input", "alternateOf", "urn:entity:output") in materialized


def test_reserved_inverse_alias_is_normalized_by_reversing_endpoints() -> None:
    graph = _graph_with_core_resources()
    graph.add_assertion("urn:entity:input", "hadDerivation", "urn:entity:output")
    assert ProvAssertion.resource(
        "urn:entity:output", "wasDerivedFrom", "urn:entity:input"
    ) in graph.explicit_assertions


def test_qualified_event_time_implies_direct_time_property() -> None:
    graph = _graph_with_core_resources()
    graph.add_resource("urn:influence:generation", "Generation")
    instant = ProvLiteral.datetime(datetime(2026, 8, 14, 4, 0, tzinfo=timezone.utc))
    graph.add_assertion("urn:entity:output", "qualifiedGeneration", "urn:influence:generation")
    graph.add_assertion("urn:influence:generation", "activity", "urn:activity:transform")
    graph.add_assertion("urn:influence:generation", "atTime", instant)
    materialized = graph.materialized_assertions()
    assert ProvAssertion.literal("urn:entity:output", "generatedAtTime", instant) in materialized


def test_rdf_serialization_uses_exact_prov_namespace_and_xsd_datetime() -> None:
    graph = _graph_with_core_resources()
    instant = ProvLiteral.datetime(datetime(2026, 8, 14, 4, 0, tzinfo=timezone.utc))
    graph.add_assertion("urn:activity:transform", "startedAtTime", instant)
    rdf_graph = graph.to_rdflib(materialize=True)
    assert (URIRef("urn:entity:input"), RDF.type, PROV.Entity) in rdf_graph
    assert (
        URIRef("urn:activity:transform"),
        PROV.startedAtTime,
        Literal("2026-08-14T04:00:00+00:00", datatype=XSD.dateTime),
    ) in rdf_graph


def test_sql_migration_seeds_every_class_relation_and_qualification() -> None:
    sql_path = Path(__file__).resolve().parents[1] / "migrations" / "0017_prov_o_standard_relations.sql"
    sql = sql_path.read_text()
    for name in EXPECTED_CLASS_NAMES:
        assert class_code(name) in sql
        assert f"http://www.w3.org/ns/prov#{name}" in sql
    for name in EXPECTED_RELATION_NAMES:
        assert relation_code(name) in sql
        assert f"http://www.w3.org/ns/prov#{name}" in sql
    for unqualified, (qualified, influence_class, influencer) in EXPECTED_QUALIFICATIONS.items():
        assert relation_code(unqualified) in sql
        assert relation_code(qualified) in sql
        assert class_code(influence_class) in sql
        assert relation_code(influencer) in sql


def test_sql_migration_uses_only_multiword_snake_case_table_names() -> None:
    import re

    sql = (Path(__file__).resolve().parents[1] / "migrations" / "0017_prov_o_standard_relations.sql").read_text()
    names = re.findall(r"create table(?: if not exists)?\s+([a-z_]+)", sql, flags=re.IGNORECASE)
    assert names
    assert all(len(name.split("_")) >= 2 for name in names)


def test_registry_spec_accessors_and_inverse_iri_use_exact_namespace() -> None:
    assert PROV_CLASSES["Entity"].iri == "http://www.w3.org/ns/prov#Entity"
    assert PROV_CLASSES["Entity"].code == "prov_entity"
    assert PROV_RELATIONS["used"].iri == "http://www.w3.org/ns/prov#used"
    assert PROV_RELATIONS["used"].code == "prov_used"
    assert (
        PROV_RECOMMENDED_INVERSES["actedOnBehalfOf"].inverse_iri
        == "http://www.w3.org/ns/prov#hadDelegate"
    )


def test_literal_contract_rejects_conflicts_invalid_language_and_naive_time() -> None:
    with pytest.raises(ProvValidationError, match="both datatype_iri and language_tag"):
        ProvLiteral("x", datatype_iri=str(XSD.string), language_tag="en")
    with pytest.raises(ProvValidationError, match="language_tag"):
        ProvLiteral("x", language_tag="not_a_tag!")
    with pytest.raises(ProvValidationError, match="timezone-aware"):
        ProvLiteral.datetime(datetime(2026, 8, 14, 4, 0))
    assert ProvLiteral("bonjour", language_tag="fr").to_rdflib() == Literal("bonjour", lang="fr")


def test_assertion_requires_exactly_one_object_kind() -> None:
    with pytest.raises(ProvValidationError, match="exactly one"):
        ProvAssertion("urn:s", "used")
    with pytest.raises(ProvValidationError, match="exactly one"):
        ProvAssertion(
            "urn:s",
            "used",
            object_resource_iri="urn:o",
            object_literal=ProvLiteral("x"),
        )


def test_resource_registration_and_name_normalization_fail_closed() -> None:
    graph = ProvGraph()
    with pytest.raises(ProvValidationError, match="resource_iri"):
        graph.add_resource("", "Entity")
    with pytest.raises(ProvValidationError, match="at least one"):
        graph.add_resource("urn:empty")
    with pytest.raises(ProvValidationError, match="unknown PROV-O class"):
        graph.add_resource("urn:bad", "NotAClass")

    graph.add_resource("urn:e", "prov:Entity")
    graph.add_resource("urn:a", "http://www.w3.org/ns/prov#Activity")
    assert graph.resource_types == {
        "urn:e": frozenset({"Entity"}),
        "urn:a": frozenset({"Activity"}),
    }


def test_assertion_name_and_endpoint_validation_fail_closed() -> None:
    graph = _graph_with_core_resources()
    with pytest.raises(ProvValidationError, match="unknown PROV-O relation"):
        graph.add_assertion("urn:entity:input", "notARelation", "urn:entity:output")
    with pytest.raises(ProvValidationError, match="subject resource"):
        graph.add_assertion("urn:missing", "prov:wasDerivedFrom", "urn:entity:input")
    with pytest.raises(ProvValidationError, match="object resource"):
        graph.add_assertion(
            "urn:entity:output",
            "http://www.w3.org/ns/prov#wasDerivedFrom",
            "urn:missing",
        )
    with pytest.raises(ProvValidationError, match="object.*Entity"):
        graph.add_assertion("urn:activity:transform", "used", "urn:role:reviewer")
    with pytest.raises(ProvValidationError, match="requires datatype"):
        graph.add_assertion(
            "urn:activity:transform",
            "startedAtTime",
            ProvLiteral("2026-08-14T04:00:00Z"),
        )
    with pytest.raises(ProvValidationError, match="cannot reverse a literal"):
        graph.add_assertion(
            "urn:entity:input",
            "hadDerivation",
            ProvLiteral("invalid"),
        )


def test_rdf_serialization_covers_resource_and_literal_objects_without_materialization() -> None:
    graph = _graph_with_core_resources()
    graph.add_assertion("urn:activity:transform", "used", "urn:entity:input")
    graph.add_assertion("urn:entity:input", "value", ProvLiteral("raw value"))
    rdf_graph = graph.to_rdflib()
    assert (
        URIRef("urn:activity:transform"),
        PROV.used,
        URIRef("urn:entity:input"),
    ) in rdf_graph
    assert (
        URIRef("urn:entity:input"),
        PROV.value,
        Literal("raw value"),
    ) in rdf_graph


def test_every_public_callable_has_a_docstring() -> None:
    import inspect

    module = sys.modules["lineageweave.prov_o"]

    missing: list[str] = []
    for name, value in vars(module).items():
        if name.startswith("_"):
            continue
        if inspect.isfunction(value) or inspect.isclass(value):
            if value.__module__ == module.__name__ and not inspect.getdoc(value):
                missing.append(name)
        if inspect.isclass(value) and value.__module__ == module.__name__:
            for member_name, member in vars(value).items():
                if member_name.startswith("_"):
                    continue
                target = member.fget if isinstance(member, property) else member
                if callable(target) and not inspect.getdoc(target):
                    missing.append(f"{name}.{member_name}")
    assert missing == []


def test_support_profile_imports_prov_o_and_maps_product_classes() -> None:
    from rdflib.namespace import OWL, RDFS

    profile_path = (
        Path(__file__).resolve().parents[1]
        / "docs"
        / "ontology"
        / "prov-o-support-profile.ttl"
    )
    profile = Graph().parse(profile_path, format="turtle")
    ontology_iri = URIRef(
        "https://contextualwisdomlab.github.io/LineageWeave/ontology/prov-o-support-profile.ttl"
    )
    local = Namespace("https://contextualwisdomlab.github.io/LineageWeave/ontology#")
    legacy = Namespace("https://contextualwisdomlab.github.io/lineageweave/ontology#")
    assert (
        ontology_iri,
        OWL.imports,
        URIRef("http://www.w3.org/ns/prov-o#"),
    ) in profile
    assert (
        ontology_iri,
        OWL.imports,
        URIRef(
            "https://contextualwisdomlab.github.io/LineageWeave/ontology/namespace-compatibility.ttl"
        ),
    ) in profile
    assert (local.Post, RDFS.subClassOf, PROV.Entity) in profile
    assert (local.Person, RDFS.subClassOf, PROV.Person) in profile
    assert (local.CorporateEntity, RDFS.subClassOf, PROV.Organization) in profile
    assert (local.Team, RDFS.subClassOf, PROV.Organization) in profile
    assert not any(str(subject).startswith(str(legacy)) for subject in profile.subjects())

    compatibility = Graph().parse(
        profile_path.with_name("namespace-compatibility.ttl"), format="turtle"
    )
    assert (legacy.Post, RDF.type, OWL.Class) in compatibility
    assert (local.Post, OWL.equivalentClass, legacy.Post) in compatibility
