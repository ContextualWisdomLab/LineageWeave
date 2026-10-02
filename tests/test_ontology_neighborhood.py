"""Ontology neighborhood assembler: typed facts, not Event Lineage."""

from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timedelta, timezone

import pytest

from lineageweave.knowledge_graph import (
    EDGE_AFFILIATION,
    EDGE_CO_MENTION,
    EDGE_MENTION,
    EDGE_MENTION_ORGANIZATION,
    EDGE_MENTION_PROJECT,
    EDGE_MENTION_TEAM,
    EDGE_SUPPORTS_OCCUPATIONAL_CONSTRUCT,
    EDGE_TEAM_AFFILIATION,
    NODE_CORPORATE_ENTITY,
    NODE_PERSON,
    NODE_POST,
    NODE_OCCUPATIONAL_CONSTRUCT,
    NODE_PROJECT,
    NODE_TEAM,
)
from lineageweave.ontology import LW, ontology_node_iri
from lineageweave.ontology_neighborhood import (
    HARD_MAXIMUM_NODES,
    PROPERTY_AFFILIATED_WITH,
    PROPERTY_CO_MENTIONED_WITH,
    PROPERTY_MENTIONS,
    PROPERTY_MENTIONS_ORGANIZATION,
    PROPERTY_MENTIONS_PROJECT,
    PROPERTY_MENTIONS_TEAM,
    PROPERTY_SUPPORTS_OCCUPATIONAL_CONSTRUCT,
    PROPERTY_OWL_SUBCLASS_OF,
    PROPERTY_SKOS_BROADER,
    PROPERTY_TEAM_AFFILIATED_WITH,
    SKOS_BROADER_IRI,
    TRUTH_AUTHORITATIVE,
    TRUTH_INFERRED,
    TRUTH_OBSERVED,
    TRUTH_PROPOSED,
    NeighborhoodFact,
    OntologyGraphEdge,
    OntologyNeighborhood,
    OntologyNeighborhoodError,
    OntologyNodeMetadata,
    OntologyVoiceAssignment,
    assemble_ontology_neighborhood,
    canonicalize_property_code,
    fact_from_knowledge_graph_edge,
    skos_broader_fact,
)

POST_ID = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa1"
PERSON_ID = "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbb1"
CORP_ID = "cccccccc-cccc-cccc-cccc-ccccccccccc1"
GROUP_ID = "dddddddd-dddd-dddd-dddd-ddddddddddd1"
HIDDEN_PERSON = "eeeeeeee-eeee-eeee-eeee-eeeeeeeeeee1"
TEAM_ID = "ffffffff-ffff-ffff-ffff-fffffffffff1"
PROJECT_ID = "demo-project"
CONSTRUCT_ID = "99999999-9999-9999-9999-999999999999"
TZ = timezone.utc
T0 = datetime(2026, 1, 10, 12, 0, tzinfo=TZ)
T_LATE = datetime(2026, 1, 20, 12, 0, tzinfo=TZ)
CUTOFF = datetime(2026, 1, 15, 12, 0, tzinfo=TZ)


def _labels() -> dict[tuple[str, str], str]:
    return {
        (NODE_POST, POST_ID): "Demo public post",
        (NODE_PERSON, PERSON_ID): "Test Person",
        (NODE_CORPORATE_ENTITY, CORP_ID): "Demo Corp",
        (NODE_CORPORATE_ENTITY, GROUP_ID): "Demo Group",
        (NODE_PERSON, HIDDEN_PERSON): "Hidden Person",
        (NODE_TEAM, TEAM_ID): "Demo Team",
        (NODE_PROJECT, PROJECT_ID): "Demo Project",
        (NODE_OCCUPATIONAL_CONSTRUCT, CONSTRUCT_ID): "Problem Sensitivity",
    }


def _mention_affiliation() -> list[NeighborhoodFact]:
    mention = fact_from_knowledge_graph_edge(
        source_node_type_code=NODE_PERSON,
        source_node_id=PERSON_ID,
        target_node_type_code=NODE_POST,
        target_node_id=POST_ID,
        edge_type_code=EDGE_MENTION,
        recorded_at=T0,
        evidence_references=(POST_ID,),
        provenance_reference="kg-edge-mention",
    )
    affiliation = fact_from_knowledge_graph_edge(
        source_node_type_code=NODE_PERSON,
        source_node_id=PERSON_ID,
        target_node_type_code=NODE_CORPORATE_ENTITY,
        target_node_id=CORP_ID,
        edge_type_code=EDGE_AFFILIATION,
        recorded_at=T0,
        evidence_references=(POST_ID,),
        provenance_reference="kg-edge-affiliation",
    )
    return [mention, affiliation]


def test_post_mentions_person_affiliated_with_corporate_entity_round_trips() -> None:
    neighborhood = assemble_ontology_neighborhood(
        focus_node_type_code=NODE_POST,
        focus_node_id=POST_ID,
        facts=_mention_affiliation(),
        labels=_labels(),
        maximum_depth=2,
    )
    properties = {(edge.source_node_id, edge.property_code, edge.target_node_id) for edge in neighborhood.edges}
    assert (POST_ID, PROPERTY_MENTIONS, PERSON_ID) in properties
    assert (PERSON_ID, PROPERTY_AFFILIATED_WITH, CORP_ID) in properties
    mentions = next(edge for edge in neighborhood.edges if edge.property_code == PROPERTY_MENTIONS)
    assert mentions.ontology_property_iri == str(LW.mentions)
    assert mentions.truth_status_code == TRUTH_OBSERVED
    person = next(node for node in neighborhood.nodes if node.node_id == PERSON_ID)
    assert person.evidence_count == 1
    document = neighborhood.jsonld_document()
    assert document["@context"]["lw"] == str(LW)
    iris = {node.ontology_class_iri for node in neighborhood.nodes}
    assert str(LW.Post) in iris
    assert str(LW.Person) in iris
    assert str(LW.CorporateEntity) in iris
    rows = neighborhood.exact_value_rows()
    assert {row["property_code"] for row in rows} == {PROPERTY_MENTIONS, PROPERTY_AFFILIATED_WITH}
    assert all(row["source_label"] and row["target_label"] for row in rows)


def test_jsonld_preserves_available_system_and_valid_times() -> None:
    fact = NeighborhoodFact(
        source_node_type_code=NODE_PERSON,
        source_node_id=PERSON_ID,
        target_node_type_code=NODE_CORPORATE_ENTITY,
        target_node_id=CORP_ID,
        property_code=PROPERTY_AFFILIATED_WITH,
        truth_status_code=TRUTH_OBSERVED,
        recorded_at=T0,
        valid_from=T0,
        valid_to=T_LATE,
        evidence_references=(POST_ID,),
    )
    neighborhood = assemble_ontology_neighborhood(
        focus_node_type_code=NODE_PERSON,
        focus_node_id=PERSON_ID,
        facts=[fact],
        labels=_labels(),
        node_metadata={
            (NODE_PERSON, PERSON_ID): OntologyNodeMetadata(recorded_at=T0),
        },
    )

    document = neighborhood.jsonld_document()
    assert document["@context"]["time"] == "http://www.w3.org/2006/time#"
    node_item = next(item for item in document["@graph"] if item["@id"].endswith(PERSON_ID))
    assert node_item["prov:generatedAtTime"]["@value"] == T0.isoformat()
    assert "time:hasBeginning" not in node_item
    edge_item = next(item for item in document["@graph"] if item["@id"].startswith("lw:edge/"))
    assert edge_item["prov:generatedAtTime"]["@type"] == "xsd:dateTimeStamp"
    assert edge_item["time:hasBeginning"]["time:inXSDDateTimeStamp"]["@value"] == T0.isoformat()
    assert edge_item["time:hasEnd"]["time:inXSDDateTimeStamp"]["@value"] == T_LATE.isoformat()


def test_post_mentions_project_round_trips_as_proposed_evidence() -> None:
    fact = fact_from_knowledge_graph_edge(
        source_node_type_code=NODE_POST,
        source_node_id=POST_ID,
        target_node_type_code=NODE_PROJECT,
        target_node_id=PROJECT_ID,
        edge_type_code=EDGE_MENTION_PROJECT,
        recorded_at=T0,
        evidence_references=(POST_ID,),
        provenance_reference="post_project_mention",
        truth_status_code=TRUTH_PROPOSED,
    )
    neighborhood = assemble_ontology_neighborhood(
        focus_node_type_code=NODE_POST,
        focus_node_id=POST_ID,
        facts=[fact],
        labels=_labels(),
    )

    edge = neighborhood.edges[0]
    project = next(node for node in neighborhood.nodes if node.node_type_code == NODE_PROJECT)
    assert edge.property_code == PROPERTY_MENTIONS_PROJECT
    assert edge.ontology_property_iri == str(LW.mentionsProject)
    assert edge.property_label == "mentions project"
    assert edge.truth_status_code == TRUTH_PROPOSED
    assert project.ontology_class_iri == str(LW.Project)
    assert project.shape_code == "diamond"


def test_post_supports_occupational_construct_without_truth_promotion() -> None:
    fact = fact_from_knowledge_graph_edge(
        source_node_type_code=NODE_POST,
        source_node_id=POST_ID,
        target_node_type_code=NODE_OCCUPATIONAL_CONSTRUCT,
        target_node_id=CONSTRUCT_ID,
        edge_type_code=EDGE_SUPPORTS_OCCUPATIONAL_CONSTRUCT,
        recorded_at=T0,
        evidence_references=(POST_ID,),
        provenance_reference="post_occupational_construct_assertion",
        truth_status_code=TRUTH_INFERRED,
    )
    neighborhood = assemble_ontology_neighborhood(
        focus_node_type_code=NODE_POST,
        focus_node_id=POST_ID,
        facts=[fact],
        labels=_labels(),
        allowed_property_codes=["edge_supports_occupational_construct"],
    )

    edge = neighborhood.edges[0]
    construct = next(
        node
        for node in neighborhood.nodes
        if node.node_type_code == NODE_OCCUPATIONAL_CONSTRUCT
    )
    assert edge.property_code == PROPERTY_SUPPORTS_OCCUPATIONAL_CONSTRUCT
    assert edge.ontology_property_iri == str(LW.supportsOccupationalConstruct)
    assert edge.truth_status_code == TRUTH_INFERRED
    assert edge.evidence_references == (POST_ID,)
    assert construct.ontology_class_iri == str(LW.OccupationalConstruct)
    assert construct.shape_code == "rounded-rectangle"


def test_jsonld_keeps_colliding_identifiers_typed() -> None:
    facts = [
        fact_from_knowledge_graph_edge(
            source_node_type_code=NODE_PERSON,
            source_node_id=POST_ID,
            target_node_type_code=NODE_POST,
            target_node_id=POST_ID,
            edge_type_code=EDGE_MENTION,
            recorded_at=T0,
            evidence_references=(POST_ID,),
        ),
        fact_from_knowledge_graph_edge(
            source_node_type_code=NODE_PERSON,
            source_node_id=POST_ID,
            target_node_type_code=NODE_CORPORATE_ENTITY,
            target_node_id=CORP_ID,
            edge_type_code=EDGE_AFFILIATION,
            recorded_at=T0,
            evidence_references=(POST_ID,),
        ),
    ]
    neighborhood = assemble_ontology_neighborhood(
        focus_node_type_code=NODE_POST,
        focus_node_id=POST_ID,
        facts=facts,
        labels={
            (NODE_POST, POST_ID): "Test post",
            (NODE_PERSON, POST_ID): "Test person",
            (NODE_CORPORATE_ENTITY, CORP_ID): "Test organization",
        },
        maximum_depth=2,
    )
    edge_ids = {
        item["@id"]: item
        for item in neighborhood.jsonld_document()["@graph"]
        if str(item["@id"]).startswith("lw:edge/")
    }
    mentions = next(item for key, item in edge_ids.items() if "/mentions:" in str(key))
    assert mentions["rdf:subject"]["@id"] == ontology_node_iri(NODE_POST, POST_ID)


def test_jsonld_emits_direct_and_reified_edge_semantics() -> None:
    """A typed edge denotes the same assertion directly and by reification."""
    neighborhood = assemble_ontology_neighborhood(
        focus_node_type_code=NODE_POST,
        focus_node_id=POST_ID,
        facts=_mention_affiliation(),
        labels=_labels(),
        maximum_depth=2,
    )
    items = neighborhood.jsonld_document()["@graph"]
    post_iri = ontology_node_iri(NODE_POST, POST_ID)
    person_iri = ontology_node_iri(NODE_PERSON, PERSON_ID)
    direct = next(
        item
        for item in items
        if item.get("@id") == post_iri and str(LW.mentions) in item
    )
    statement = next(
        item for item in items if "rdf:Statement" in item.get("@type", [])
    )

    assert direct[str(LW.mentions)]["@id"] == person_iri
    assert statement["rdf:subject"]["@id"] == post_iri
    assert statement["rdf:predicate"]["@id"] == str(LW.mentions)
    assert statement["rdf:object"]["@id"] == person_iri


def test_jsonld_percent_encodes_project_iri_like_the_rdf_projection() -> None:
    """Unicode candidate ids denote one resource in JSON-LD and RDF."""
    project_id = f"{POST_ID}/설비-개선"
    fact = fact_from_knowledge_graph_edge(
        source_node_type_code=NODE_POST,
        source_node_id=POST_ID,
        target_node_type_code=NODE_PROJECT,
        target_node_id=project_id,
        edge_type_code=EDGE_MENTION_PROJECT,
        recorded_at=T0,
        evidence_references=(POST_ID,),
        truth_status_code=TRUTH_PROPOSED,
    )
    neighborhood = assemble_ontology_neighborhood(
        focus_node_type_code=NODE_POST,
        focus_node_id=POST_ID,
        facts=[fact],
        labels={
            (NODE_POST, POST_ID): "Synthetic source",
            (NODE_PROJECT, project_id): "설비 개선",
        },
    )

    project = next(
        item
        for item in neighborhood.jsonld_document()["@graph"]
        if item.get("@type") == str(LW.Project)
    )
    assert project["@id"] == ontology_node_iri(NODE_PROJECT, project_id)
    assert "%EC%84%A4%EB%B9%84-%EA%B0%9C%EC%84%A0" in project["@id"]


def test_skos_broader_is_distinct_from_owl_class_subsumption() -> None:
    facts = _mention_affiliation() + [
        skos_broader_fact(
            narrower_entity_id=CORP_ID,
            broader_entity_id=GROUP_ID,
            recorded_at=T0,
            provenance_reference="corporate_entity.parent_entity_id",
        )
    ]
    neighborhood = assemble_ontology_neighborhood(
        focus_node_type_code=NODE_CORPORATE_ENTITY,
        focus_node_id=CORP_ID,
        facts=facts,
        labels=_labels(),
        maximum_depth=2,
    )
    broader = next(edge for edge in neighborhood.edges if edge.property_code == PROPERTY_SKOS_BROADER)
    assert broader.ontology_property_iri == SKOS_BROADER_IRI
    assert broader.truth_status_code == TRUTH_AUTHORITATIVE
    assert broader.source_node_id == CORP_ID
    assert broader.target_node_id == GROUP_ID
    assert all(edge.ontology_property_iri != str(LW) + "subClassOf" for edge in neighborhood.edges)
    with pytest.raises(OntologyNeighborhoodError) as raised:
        assemble_ontology_neighborhood(
            focus_node_type_code=NODE_PERSON,
            focus_node_id=PERSON_ID,
            facts=[
                NeighborhoodFact(
                    source_node_type_code=NODE_PERSON,
                    source_node_id=PERSON_ID,
                    target_node_type_code=NODE_CORPORATE_ENTITY,
                    target_node_id=CORP_ID,
                    property_code=PROPERTY_OWL_SUBCLASS_OF,
                    truth_status_code=TRUTH_AUTHORITATIVE,
                    recorded_at=T0,
                )
            ],
            labels=_labels(),
        )
    assert raised.value.code == "owl_subclass_not_instance"


def test_inferred_edge_is_never_serialized_as_authoritative() -> None:
    inferred = NeighborhoodFact(
        source_node_type_code=NODE_PERSON,
        source_node_id=PERSON_ID,
        target_node_type_code=NODE_CORPORATE_ENTITY,
        target_node_id=CORP_ID,
        property_code=PROPERTY_AFFILIATED_WITH,
        truth_status_code=TRUTH_INFERRED,
        recorded_at=T0,
        evidence_references=(POST_ID,),
    )
    broader = skos_broader_fact(
        narrower_entity_id=CORP_ID,
        broader_entity_id=GROUP_ID,
        recorded_at=T0,
    )
    neighborhood = assemble_ontology_neighborhood(
        focus_node_type_code=NODE_PERSON,
        focus_node_id=PERSON_ID,
        facts=[inferred, broader],
        labels=_labels(),
    )
    inferred_edge = next(edge for edge in neighborhood.edges if edge.property_code == PROPERTY_AFFILIATED_WITH)
    assert inferred_edge.truth_status_code == TRUTH_INFERRED
    assert inferred_edge.truth_status_code != TRUTH_AUTHORITATIVE
    corporate_node = next(node for node in neighborhood.nodes if node.node_id == CORP_ID)
    assert corporate_node.truth_status_code != TRUTH_AUTHORITATIVE
    assert corporate_node.evidence_count == 1
    document = neighborhood.jsonld_document()
    node_item = next(item for item in document["@graph"] if item["@id"].endswith(f"/{CORP_ID}"))
    assert node_item.get("lw:truthStatus") != TRUTH_AUTHORITATIVE
    statuses = [item["lw:truthStatus"] for item in document["@graph"] if "lw:truthStatus" in item]
    assert TRUTH_INFERRED in statuses
    assert TRUTH_AUTHORITATIVE in statuses


def test_hidden_endpoint_removes_edge_without_count_side_channel() -> None:
    hidden_affiliation = fact_from_knowledge_graph_edge(
        source_node_type_code=NODE_PERSON,
        source_node_id=HIDDEN_PERSON,
        target_node_type_code=NODE_CORPORATE_ENTITY,
        target_node_id=CORP_ID,
        edge_type_code=EDGE_AFFILIATION,
        recorded_at=T0,
        evidence_references=(POST_ID,),
    )
    neighborhood = assemble_ontology_neighborhood(
        focus_node_type_code=NODE_CORPORATE_ENTITY,
        focus_node_id=CORP_ID,
        facts=_mention_affiliation() + [hidden_affiliation],
        labels=_labels(),
        hidden_node_keys=frozenset({f"{NODE_PERSON}:{HIDDEN_PERSON}"}),
    )
    assert HIDDEN_PERSON not in {node.node_id for node in neighborhood.nodes}
    assert HIDDEN_PERSON not in {edge.source_node_id for edge in neighborhood.edges}
    assert HIDDEN_PERSON not in {edge.target_node_id for edge in neighborhood.edges}
    payload = neighborhood.jsonld_document()
    serialized = str(payload)
    assert HIDDEN_PERSON not in serialized
    assert "omitted" not in serialized.lower()
    assert neighborhood.limitation_code != "hidden_count"


def test_cutoff_excludes_later_available_evidence() -> None:
    late = fact_from_knowledge_graph_edge(
        source_node_type_code=NODE_PERSON,
        source_node_id=PERSON_ID,
        target_node_type_code=NODE_CORPORATE_ENTITY,
        target_node_id=CORP_ID,
        edge_type_code=EDGE_AFFILIATION,
        recorded_at=T_LATE,
        evidence_references=(POST_ID,),
    )
    neighborhood = assemble_ontology_neighborhood(
        focus_node_type_code=NODE_POST,
        focus_node_id=POST_ID,
        facts=[_mention_affiliation()[0], late],
        labels=_labels(),
        knowledge_cutoff=CUTOFF,
        maximum_depth=2,
    )
    assert all(edge.property_code != PROPERTY_AFFILIATED_WITH for edge in neighborhood.edges)
    assert any(edge.property_code == PROPERTY_MENTIONS for edge in neighborhood.edges)


def test_unknown_property_and_unlabeled_edge_fail_closed() -> None:
    with pytest.raises(OntologyNeighborhoodError) as unknown:
        canonicalize_property_code("edge_invented")
    assert unknown.value.code == "unknown_property"
    neighborhood = assemble_ontology_neighborhood(
        focus_node_type_code=NODE_POST,
        focus_node_id=POST_ID,
        facts=_mention_affiliation(),
        labels={(NODE_POST, POST_ID): "Demo public post", (NODE_PERSON, PERSON_ID): "Test Person"},
    )
    assert [edge.property_code for edge in neighborhood.edges] == [PROPERTY_MENTIONS]
    assert [node.node_id for node in neighborhood.nodes] == [POST_ID, PERSON_ID]


def test_naive_timestamp_and_invalid_interval_fail_closed() -> None:
    with pytest.raises(OntologyNeighborhoodError) as naive:
        assemble_ontology_neighborhood(
            focus_node_type_code=NODE_PERSON,
            focus_node_id=PERSON_ID,
            facts=[
                NeighborhoodFact(
                    source_node_type_code=NODE_PERSON,
                    source_node_id=PERSON_ID,
                    target_node_type_code=NODE_CORPORATE_ENTITY,
                    target_node_id=CORP_ID,
                    property_code=PROPERTY_AFFILIATED_WITH,
                    truth_status_code=TRUTH_OBSERVED,
                    recorded_at=datetime(2026, 1, 10, 12, 0),
                )
            ],
            labels=_labels(),
        )
    assert naive.value.code == "naive_timestamp"
    with pytest.raises(OntologyNeighborhoodError) as interval:
        assemble_ontology_neighborhood(
            focus_node_type_code=NODE_PERSON,
            focus_node_id=PERSON_ID,
            facts=[
                NeighborhoodFact(
                    source_node_type_code=NODE_PERSON,
                    source_node_id=PERSON_ID,
                    target_node_type_code=NODE_CORPORATE_ENTITY,
                    target_node_id=CORP_ID,
                    property_code=PROPERTY_AFFILIATED_WITH,
                    truth_status_code=TRUTH_OBSERVED,
                    recorded_at=T0,
                    valid_from=T0,
                    valid_to=T0 - timedelta(days=1),
                )
            ],
            labels=_labels(),
        )
    assert interval.value.code == "invalid_interval"


def test_excessive_depth_and_malformed_cursor_fail_closed() -> None:
    with pytest.raises(OntologyNeighborhoodError) as depth:
        assemble_ontology_neighborhood(
            focus_node_type_code=NODE_POST,
            focus_node_id=POST_ID,
            facts=_mention_affiliation(),
            labels=_labels(),
            maximum_depth=99,
        )
    assert depth.value.code == "excessive_depth"
    with pytest.raises(OntologyNeighborhoodError) as cursor:
        assemble_ontology_neighborhood(
            focus_node_type_code=NODE_POST,
            focus_node_id=POST_ID,
            facts=_mention_affiliation(),
            labels=_labels(),
            cursor="1",
        )
    assert cursor.value.code == "malformed_cursor"


def test_invalid_focus_id_is_distinct_from_unknown_node_type() -> None:
    for invalid_id in ("", " padded", "padded "):
        with pytest.raises(OntologyNeighborhoodError) as raised:
            assemble_ontology_neighborhood(
                focus_node_type_code=NODE_POST,
                focus_node_id=invalid_id,
                facts=[],
                labels=_labels(),
            )
        assert raised.value.code == "invalid_focus_id"


def test_node_metadata_is_catalog_owned_and_missing_values_stay_absent() -> None:
    metadata = {
        (NODE_PERSON, PERSON_ID): OntologyNodeMetadata(
            truth_status_code=TRUTH_OBSERVED,
            recorded_at=T0,
        )
    }
    with_metadata = assemble_ontology_neighborhood(
        focus_node_type_code=NODE_PERSON,
        focus_node_id=PERSON_ID,
        facts=[_mention_affiliation()[1]],
        labels=_labels(),
        node_metadata=metadata,
    )
    person = next(node for node in with_metadata.nodes if node.node_id == PERSON_ID)
    assert person.truth_status_code == TRUTH_OBSERVED
    assert person.recorded_at == T0
    without_metadata = assemble_ontology_neighborhood(
        focus_node_type_code=NODE_PERSON,
        focus_node_id=PERSON_ID,
        facts=[],
        labels=_labels(),
    )
    assert without_metadata.nodes[0].truth_status_code is None
    assert without_metadata.nodes[0].recorded_at is None

    with pytest.raises(OntologyNeighborhoodError, match="node recorded_at"):
        assemble_ontology_neighborhood(
            focus_node_type_code=NODE_PERSON,
            focus_node_id=PERSON_ID,
            facts=[],
            labels=_labels(),
            node_metadata={
                (NODE_PERSON, PERSON_ID): OntologyNodeMetadata(
                    recorded_at=datetime(2026, 1, 10, 12, 0)
                )
            },
        )

    with pytest.raises(OntologyNeighborhoodError) as unknown_truth:
        assemble_ontology_neighborhood(
            focus_node_type_code=NODE_PERSON,
            focus_node_id=PERSON_ID,
            facts=[],
            labels=_labels(),
            node_metadata={
                (NODE_PERSON, PERSON_ID): OntologyNodeMetadata(
                    truth_status_code="truth_unregistered"
                )
            },
        )
    assert unknown_truth.value.code == "unknown_truth_status"


def test_truncation_is_flagged_without_omission_counts() -> None:
    neighborhood = assemble_ontology_neighborhood(
        focus_node_type_code=NODE_POST,
        focus_node_id=POST_ID,
        facts=_mention_affiliation(),
        labels=_labels(),
        maximum_depth=2,
        maximum_edges=1,
    )
    assert neighborhood.truncated is True
    assert neighborhood.next_cursor is not None
    assert neighborhood.next_cursor.startswith("after:")
    assert neighborhood.limitation_code == "neighborhood_truncated"
    page_two = assemble_ontology_neighborhood(
        focus_node_type_code=NODE_POST,
        focus_node_id=POST_ID,
        facts=_mention_affiliation(),
        labels=_labels(),
        maximum_depth=2,
        maximum_edges=1,
        cursor=neighborhood.next_cursor,
    )
    assert {edge.edge_id for edge in neighborhood.edges}.isdisjoint({edge.edge_id for edge in page_two.edges})


def test_empty_visible_neighborhood_names_the_empty_limitation() -> None:
    neighborhood = assemble_ontology_neighborhood(
        focus_node_type_code=NODE_POST,
        focus_node_id=POST_ID,
        facts=[],
        labels=_labels(),
    )
    assert neighborhood.edges == ()
    assert neighborhood.nodes[0].node_id == POST_ID
    assert neighborhood.limitation_code == "neighborhood_empty"


def test_unknown_node_type_and_unknown_truth_fail_closed() -> None:
    with pytest.raises(OntologyNeighborhoodError) as node_type:
        assemble_ontology_neighborhood(
            focus_node_type_code="node_invented",
            focus_node_id=POST_ID,
            facts=[],
            labels=_labels(),
        )
    assert node_type.value.code == "unknown_node_type"
    with pytest.raises(OntologyNeighborhoodError) as truth:
        assemble_ontology_neighborhood(
            focus_node_type_code=NODE_PERSON,
            focus_node_id=PERSON_ID,
            facts=[
                NeighborhoodFact(
                    source_node_type_code=NODE_PERSON,
                    source_node_id=PERSON_ID,
                    target_node_type_code=NODE_CORPORATE_ENTITY,
                    target_node_id=CORP_ID,
                    property_code=PROPERTY_AFFILIATED_WITH,
                    truth_status_code="truth_guessed",
                    recorded_at=T0,
                )
            ],
            labels=_labels(),
        )
    assert truth.value.code == "unknown_truth_status"


def test_allowed_property_filter_keeps_mentions_alias() -> None:
    neighborhood = assemble_ontology_neighborhood(
        focus_node_type_code=NODE_POST,
        focus_node_id=POST_ID,
        facts=_mention_affiliation(),
        labels=_labels(),
        allowed_property_codes=[EDGE_MENTION],
        maximum_depth=2,
    )
    assert {edge.property_code for edge in neighborhood.edges} == {PROPERTY_MENTIONS}


def test_hidden_focus_fails_closed() -> None:
    with pytest.raises(OntologyNeighborhoodError) as hidden:
        assemble_ontology_neighborhood(
            focus_node_type_code=NODE_PERSON,
            focus_node_id=HIDDEN_PERSON,
            facts=_mention_affiliation(),
            labels=_labels(),
            hidden_node_keys=frozenset({f"{NODE_PERSON}:{HIDDEN_PERSON}"}),
        )
    assert hidden.value.code == "focus_hidden"


def test_unbounded_request_and_empty_focus_fail_closed() -> None:
    with pytest.raises(OntologyNeighborhoodError) as nodes:
        assemble_ontology_neighborhood(
            focus_node_type_code=NODE_POST,
            focus_node_id=POST_ID,
            facts=[],
            labels=_labels(),
            maximum_nodes=HARD_MAXIMUM_NODES + 1,
        )
    assert nodes.value.code == "unbounded_request"
    with pytest.raises(OntologyNeighborhoodError) as edges:
        assemble_ontology_neighborhood(
            focus_node_type_code=NODE_POST,
            focus_node_id=POST_ID,
            facts=[],
            labels=_labels(),
            maximum_edges=0,
        )
    assert edges.value.code == "unbounded_request"
    with pytest.raises(OntologyNeighborhoodError) as empty:
        assemble_ontology_neighborhood(
            focus_node_type_code=NODE_POST,
            focus_node_id="  ",
            facts=[],
            labels=_labels(),
        )
    assert empty.value.code == "invalid_focus_id"


def test_team_and_organization_mention_edges_round_trip() -> None:
    facts = _mention_affiliation() + [
        fact_from_knowledge_graph_edge(
            source_node_type_code=NODE_TEAM,
            source_node_id=TEAM_ID,
            target_node_type_code=NODE_POST,
            target_node_id=POST_ID,
            edge_type_code=EDGE_MENTION_TEAM,
            recorded_at=T0,
            evidence_references=(POST_ID,),
        ),
        fact_from_knowledge_graph_edge(
            source_node_type_code=NODE_TEAM,
            source_node_id=TEAM_ID,
            target_node_type_code=NODE_CORPORATE_ENTITY,
            target_node_id=CORP_ID,
            edge_type_code=EDGE_TEAM_AFFILIATION,
            recorded_at=T0,
            evidence_references=(POST_ID,),
        ),
        fact_from_knowledge_graph_edge(
            source_node_type_code=NODE_CORPORATE_ENTITY,
            source_node_id=CORP_ID,
            target_node_type_code=NODE_POST,
            target_node_id=POST_ID,
            edge_type_code=EDGE_MENTION_ORGANIZATION,
            recorded_at=T0,
            evidence_references=(POST_ID,),
        ),
        fact_from_knowledge_graph_edge(
            source_node_type_code=NODE_PERSON,
            source_node_id=PERSON_ID,
            target_node_type_code=NODE_PERSON,
            target_node_id=HIDDEN_PERSON,
            edge_type_code=EDGE_CO_MENTION,
            recorded_at=T0,
            evidence_references=(POST_ID,),
        ),
    ]
    neighborhood = assemble_ontology_neighborhood(
        focus_node_type_code=NODE_POST,
        focus_node_id=POST_ID,
        facts=facts,
        labels=_labels(),
        maximum_depth=2,
    )
    codes = {edge.property_code for edge in neighborhood.edges}
    assert PROPERTY_MENTIONS_TEAM in codes
    assert PROPERTY_TEAM_AFFILIATED_WITH in codes
    assert PROPERTY_MENTIONS_ORGANIZATION in codes
    assert PROPERTY_CO_MENTIONED_WITH in codes


def test_unknown_kg_edge_and_cutoff_validity_windows() -> None:
    with pytest.raises(OntologyNeighborhoodError) as unknown:
        fact_from_knowledge_graph_edge(
            source_node_type_code=NODE_PERSON,
            source_node_id=PERSON_ID,
            target_node_type_code=NODE_POST,
            target_node_id=POST_ID,
            edge_type_code="edge_invented",
            recorded_at=T0,
        )
    assert unknown.value.code == "unknown_property"
    too_late_start = NeighborhoodFact(
        source_node_type_code=NODE_PERSON,
        source_node_id=PERSON_ID,
        target_node_type_code=NODE_CORPORATE_ENTITY,
        target_node_id=CORP_ID,
        property_code=PROPERTY_AFFILIATED_WITH,
        truth_status_code=TRUTH_OBSERVED,
        recorded_at=T0,
        valid_from=T_LATE,
    )
    already_ended = NeighborhoodFact(
        source_node_type_code=NODE_PERSON,
        source_node_id=PERSON_ID,
        target_node_type_code=NODE_CORPORATE_ENTITY,
        target_node_id=CORP_ID,
        property_code=PROPERTY_AFFILIATED_WITH,
        truth_status_code=TRUTH_OBSERVED,
        recorded_at=T0,
        valid_to=datetime(2026, 1, 1, tzinfo=TZ),
    )
    kept = assemble_ontology_neighborhood(
        focus_node_type_code=NODE_PERSON,
        focus_node_id=PERSON_ID,
        facts=[too_late_start, already_ended, _mention_affiliation()[1]],
        labels=_labels(),
        knowledge_cutoff=CUTOFF,
    )
    assert all(edge.valid_from is None for edge in kept.edges)
    naive_valid = NeighborhoodFact(
        source_node_type_code=NODE_PERSON,
        source_node_id=PERSON_ID,
        target_node_type_code=NODE_CORPORATE_ENTITY,
        target_node_id=CORP_ID,
        property_code=PROPERTY_AFFILIATED_WITH,
        truth_status_code=TRUTH_OBSERVED,
        recorded_at=T0,
        valid_from=datetime(2026, 1, 1),
    )
    with pytest.raises(OntologyNeighborhoodError) as naive:
        assemble_ontology_neighborhood(
            focus_node_type_code=NODE_PERSON,
            focus_node_id=PERSON_ID,
            facts=[naive_valid],
            labels=_labels(),
        )
    assert naive.value.code == "naive_timestamp"
    naive_to = NeighborhoodFact(
        source_node_type_code=NODE_PERSON,
        source_node_id=PERSON_ID,
        target_node_type_code=NODE_CORPORATE_ENTITY,
        target_node_id=CORP_ID,
        property_code=PROPERTY_AFFILIATED_WITH,
        truth_status_code=TRUTH_OBSERVED,
        recorded_at=T0,
        valid_to=datetime(2026, 2, 1),
    )
    with pytest.raises(OntologyNeighborhoodError) as naive_end:
        assemble_ontology_neighborhood(
            focus_node_type_code=NODE_PERSON,
            focus_node_id=PERSON_ID,
            facts=[naive_to],
            labels=_labels(),
        )
    assert naive_end.value.code == "naive_timestamp"


def test_node_bound_truncation_drops_cursor_and_jsonld_rejects_dangling() -> None:
    neighborhood = assemble_ontology_neighborhood(
        focus_node_type_code=NODE_POST,
        focus_node_id=POST_ID,
        facts=_mention_affiliation(),
        labels=_labels(),
        maximum_depth=2,
        maximum_nodes=1,
    )
    assert neighborhood.truncated is True
    assert neighborhood.next_cursor is None
    assert len(neighborhood.nodes) == 1
    node = neighborhood.nodes[0]
    assert node.evidence_count == 0
    dangling = OntologyNeighborhood(
        focus_node_id=POST_ID,
        focus_node_type_code=NODE_POST,
        nodes=(node,),
        edges=(
            OntologyGraphEdge(
                edge_id="mentions:node_post:x:node_person:y",
                source_node_type_code=NODE_POST,
                source_node_id=POST_ID,
                target_node_type_code=NODE_PERSON,
                target_node_id=PERSON_ID,
                property_code=PROPERTY_MENTIONS,
                ontology_property_iri=str(LW.mentions),
                property_label="mentions",
                truth_status_code=TRUTH_OBSERVED,
                valid_from=T0,
                valid_to=T_LATE,
                recorded_at=T0,
                provenance_reference="kg",
                evidence_references=(POST_ID,),
            ),
        ),
        truncated=False,
        next_cursor=None,
        limitation_code=None,
    )
    with pytest.raises(OntologyNeighborhoodError) as raised:
        dangling.jsonld_document()
    assert raised.value.code == "dangling_endpoint"
    with pytest.raises(OntologyNeighborhoodError) as exact_values:
        dangling.exact_value_rows()
    assert exact_values.value.code == "dangling_endpoint"
    rows = neighborhood.exact_value_rows()
    assert rows == ()


def test_voice_assignments_join_exact_csv_rows_and_jsonld() -> None:
    """One authorized post exports the same qualified voice through both projections."""
    neighborhood = assemble_ontology_neighborhood(
        focus_node_type_code=NODE_POST,
        focus_node_id=POST_ID,
        facts=[],
        labels=_labels(),
    )
    assignment = OntologyVoiceAssignment(
        post_id=POST_ID,
        voice_type_code="vops",
        voice_type_iri=str(LW.voiceOfProcessType),
        voice_type_label="Voice of Process",
        is_primary=False,
        truth_status_code=TRUTH_OBSERVED,
        recorded_at=T0,
        effective_from=T0,
        provenance_reference="Evidence-backed additional voice",
        evidence_post_id=POST_ID,
    )
    neighborhood = replace(neighborhood, voice_assignments=(assignment,))

    row = neighborhood.exact_value_rows()[0]
    assert row["property_code"] == "hasVoiceAssignment"
    assert row["target_label"] == "Voice of Process"
    assert row["evidence_post_id"] == POST_ID
    assert row["evidence_count"] == "1"
    graph = neighborhood.jsonld_document()["@graph"]
    assignment_iri = str(LW[f"voice-assignment/{POST_ID}/vops"])
    projected = next(item for item in graph if item.get("@id") == assignment_iri)
    post_projection = next(
        item
        for item in graph
        if item.get("@id") == ontology_node_iri(NODE_POST, POST_ID)
        and str(LW.hasVoiceAssignment) in item
    )
    assert post_projection[str(LW.hasVoiceAssignment)] == [{"@id": assignment_iri}]
    assert projected[str(LW.assignedVoiceType)] == {"@id": str(LW.voiceOfProcessType)}
    assert projected[str(LW.voiceAssignmentCarryingPost)] == {
        "@id": ontology_node_iri(NODE_POST, POST_ID)
    }
    assert projected[str(LW.voiceAssignmentEvidence)] == {
        "@id": ontology_node_iri(NODE_POST, POST_ID)
    }
    assert projected["prov:wasDerivedFrom"] == {
        "@id": ontology_node_iri(NODE_POST, POST_ID)
    }

    hidden_evidence = replace(assignment, evidence_post_id=None)
    hidden_row = replace(
        neighborhood, voice_assignments=(hidden_evidence,)
    ).exact_value_rows()[0]
    assert hidden_row["evidence_post_id"] == ""
    assert hidden_row["evidence_count"] == "0"
    hidden_projection = next(
        item
        for item in replace(neighborhood, voice_assignments=(hidden_evidence,))
        .jsonld_document()["@graph"]
        if item.get("@id") == assignment_iri
    )
    assert str(LW.voiceAssignmentEvidence) not in hidden_projection
    assert "prov:wasDerivedFrom" not in hidden_projection

    imported_primary = replace(assignment, is_primary=True, evidence_post_id=None)
    primary_projection = next(
        item
        for item in replace(neighborhood, voice_assignments=(imported_primary,))
        .jsonld_document()["@graph"]
        if item.get("@id") == assignment_iri
    )
    assert str(LW.voiceAssignmentEvidence) not in primary_projection
    assert "prov:wasDerivedFrom" not in primary_projection
    assert primary_projection[str(LW.voiceAssignmentCarryingPost)] == {
        "@id": ontology_node_iri(NODE_POST, POST_ID)
    }

    with pytest.raises(OntologyNeighborhoodError, match="offset-aware"):
        replace(assignment, recorded_at=T0.replace(tzinfo=None))


def test_jsonld_keeps_every_voice_for_one_post_in_one_subject_projection() -> None:
    """Multiple Voice relations for one paged subject cannot overwrite each other."""
    neighborhood = assemble_ontology_neighborhood(
        focus_node_type_code=NODE_POST,
        focus_node_id=POST_ID,
        facts=[],
        labels=_labels(),
    )
    primary = OntologyVoiceAssignment(
        post_id=POST_ID,
        voice_type_code="voc",
        voice_type_iri=str(LW.voiceOfCustomerType),
        voice_type_label="Voice of Customer",
        is_primary=True,
        truth_status_code=TRUTH_OBSERVED,
        recorded_at=T0,
        effective_from=T0,
        provenance_reference="Imported primary voice",
        evidence_post_id=None,
    )
    additional = replace(
        primary,
        voice_type_code="vops",
        voice_type_iri=str(LW.voiceOfProcessType),
        voice_type_label="Voice of Process",
        is_primary=False,
        provenance_reference="Evidence-backed additional voice",
        evidence_post_id=POST_ID,
    )

    graph = replace(
        neighborhood, voice_assignments=(primary, additional)
    ).jsonld_document()["@graph"]
    post_iri = ontology_node_iri(NODE_POST, POST_ID)
    post_voice_projection = next(
        item
        for item in graph
        if item.get("@id") == post_iri and str(LW.hasVoiceAssignment) in item
    )

    assert post_voice_projection[str(LW.hasVoiceAssignment)] == [
        {"@id": str(LW[f"voice-assignment/{POST_ID}/voc"])},
        {"@id": str(LW[f"voice-assignment/{POST_ID}/vops"])},
    ]
    assert sum(
        item.get("@id") == post_iri and str(LW.hasVoiceAssignment) in item
        for item in graph
    ) == 1


def test_node_bound_truncation_keeps_nearer_hop_over_farther_alphabetically_earlier_type() -> None:
    """Trim by BFS distance, not by the raw "type:id" key string.

    Two hop-1 ``node_post`` neighbors and one hop-2 ``node_corporate_entity``
    neighbor straddle ``maximum_nodes``. "node_corporate_entity" sorts
    before "node_post" lexicographically, so a key-string trim would keep
    the farther corporate entity and drop a nearer post. Distance-based
    trimming must keep both nearer posts instead.
    """
    post_b_id = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa2"
    labels = {
        **_labels(),
        (NODE_POST, post_b_id): "Second post",
    }
    mention_a = fact_from_knowledge_graph_edge(
        source_node_type_code=NODE_PERSON,
        source_node_id=PERSON_ID,
        target_node_type_code=NODE_POST,
        target_node_id=POST_ID,
        edge_type_code=EDGE_MENTION,
        recorded_at=T0,
        evidence_references=(POST_ID,),
        provenance_reference="kg-edge-mention-a",
    )
    mention_b = fact_from_knowledge_graph_edge(
        source_node_type_code=NODE_PERSON,
        source_node_id=PERSON_ID,
        target_node_type_code=NODE_POST,
        target_node_id=post_b_id,
        edge_type_code=EDGE_MENTION,
        recorded_at=T0,
        evidence_references=(post_b_id,),
        provenance_reference="kg-edge-mention-b",
    )
    mention_organization = fact_from_knowledge_graph_edge(
        source_node_type_code=NODE_CORPORATE_ENTITY,
        source_node_id=CORP_ID,
        target_node_type_code=NODE_POST,
        target_node_id=POST_ID,
        edge_type_code=EDGE_MENTION_ORGANIZATION,
        recorded_at=T0,
        evidence_references=(POST_ID,),
        provenance_reference="kg-edge-mention-organization",
    )
    neighborhood = assemble_ontology_neighborhood(
        focus_node_type_code=NODE_PERSON,
        focus_node_id=PERSON_ID,
        facts=[mention_a, mention_b, mention_organization],
        labels=labels,
        maximum_depth=2,
        maximum_nodes=3,
    )
    assert neighborhood.truncated is True
    kept = {(node.node_type_code, node.node_id) for node in neighborhood.nodes}
    assert kept == {
        (NODE_PERSON, PERSON_ID),
        (NODE_POST, POST_ID),
        (NODE_POST, post_b_id),
    }
    assert (NODE_CORPORATE_ENTITY, CORP_ID) not in kept


def test_malformed_cursor_token_and_owl_alias_fail_closed() -> None:
    with pytest.raises(OntologyNeighborhoodError) as owl:
        canonicalize_property_code(PROPERTY_OWL_SUBCLASS_OF)
    assert owl.value.code == "owl_subclass_not_instance"
    with pytest.raises(OntologyNeighborhoodError) as cursor:
        assemble_ontology_neighborhood(
            focus_node_type_code=NODE_POST,
            focus_node_id=POST_ID,
            facts=_mention_affiliation(),
            labels=_labels(),
            cursor="after:not-a-visible-edge",
        )
    assert cursor.value.code == "malformed_cursor"


def test_unlabeled_focus_fails_closed() -> None:
    with pytest.raises(OntologyNeighborhoodError) as unlabeled:
        assemble_ontology_neighborhood(
            focus_node_type_code=NODE_POST,
            focus_node_id="missing-post",
            facts=[],
            labels=_labels(),
        )
    assert unlabeled.value.code == "dangling_endpoint"


def test_unlabeled_source_is_skipped_and_unknown_fact_node_type_fails_closed() -> None:
    neighborhood = assemble_ontology_neighborhood(
        focus_node_type_code=NODE_CORPORATE_ENTITY,
        focus_node_id=CORP_ID,
        facts=[_mention_affiliation()[1]],
        labels={(NODE_CORPORATE_ENTITY, CORP_ID): "Demo Corp"},
    )
    assert neighborhood.edges == ()
    with pytest.raises(OntologyNeighborhoodError) as node_type:
        assemble_ontology_neighborhood(
            focus_node_type_code=NODE_POST,
            focus_node_id=POST_ID,
            facts=[
                NeighborhoodFact(
                    source_node_type_code="node_invented",
                    source_node_id=PERSON_ID,
                    target_node_type_code=NODE_POST,
                    target_node_id=POST_ID,
                    property_code=PROPERTY_MENTIONS,
                    truth_status_code=TRUTH_OBSERVED,
                    recorded_at=T0,
                )
            ],
            labels=_labels(),
        )
    assert node_type.value.code == "unknown_node_type"
