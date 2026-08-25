"""Authorization-gated ontology neighborhood loader (ADR 0184)."""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone

import pytest

from backend.app.ontology_neighborhood_ingestion import (
    _load_facts,
    _load_labels,
    _load_node_metadata,
    _load_skos_facts,
    focus_catalog_exists,
    neighborhood_error_detail,
    neighborhood_error_http_status,
    neighborhood_to_payload,
    parse_allowed_property_query,
    visible_ontology_neighborhood,
    visible_post_ids_for_focus,
)
from lineageweave.knowledge_graph import (
    EDGE_AFFILIATION,
    EDGE_MENTION,
    EDGE_MENTION_PROJECT,
    NODE_CORPORATE_ENTITY,
    NODE_PERSON,
    NODE_POST,
    NODE_PROJECT,
    NODE_TEAM,
)
from lineageweave.ontology_neighborhood import (
    NeighborhoodFact,
    OntologyNeighborhoodError,
    OntologyNodeMetadata,
    PROPERTY_AFFILIATED_WITH,
    TRUTH_OBSERVED,
    assemble_ontology_neighborhood,
    fact_from_knowledge_graph_edge,
)

POST_ID = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa1"
PERSON_ID = "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbb1"
CORP_ID = "cccccccc-cccc-cccc-cccc-ccccccccccc1"
GROUP_ID = "dddddddd-dddd-dddd-dddd-ddddddddddd1"
TEAM_ID = "ffffffff-ffff-ffff-ffff-fffffffffff1"
PROJECT_ID = "demo-project"
T0 = datetime(2026, 1, 10, 12, 0, tzinfo=timezone.utc)


class ScriptedConn:
    """Minimal asyncpg stand-in keyed by distinctive SQL fragments."""

    def __init__(self, script: dict[str, object]) -> None:
        self.script = script
        self.calls: list[tuple[str, tuple[object, ...]]] = []

    def _match(self, sql: str) -> object | None:
        compact = " ".join(sql.split())
        hits = [(key, value) for key, value in self.script.items() if key in compact]
        if not hits:
            return None
        hits.sort(key=lambda item: len(item[0]), reverse=True)
        return hits[0][1]

    async def fetch(self, sql: str, *args: object) -> list[object]:
        self.calls.append((sql, args))
        value = self._match(sql)
        if value is None:
            return []
        if isinstance(value, list):
            return value
        return [value]

    async def fetchrow(self, sql: str, *args: object) -> object | None:
        self.calls.append((sql, args))
        value = self._match(sql)
        if isinstance(value, list):
            return value[0] if value else None
        return value

    async def fetchval(self, sql: str, *args: object) -> object | None:
        row = await self.fetchrow(sql, *args)
        if row is None:
            return None
        if isinstance(row, dict):
            return next(iter(row.values()))
        return row


def test_parse_allowed_property_query_splits_and_drops_empty() -> None:
    assert parse_allowed_property_query(None) is None
    assert parse_allowed_property_query(["  ", ","]) is None
    assert parse_allowed_property_query(["mentions, affiliatedWith", " skos_broader "]) == [
        "mentions",
        "affiliatedWith",
        "skos_broader",
    ]


def test_neighborhood_error_http_status_is_fail_closed() -> None:
    assert neighborhood_error_http_status(OntologyNeighborhoodError("focus_hidden", "x")) == 404
    assert neighborhood_error_http_status(OntologyNeighborhoodError("focus_not_visible", "x")) == 404
    assert neighborhood_error_http_status(OntologyNeighborhoodError("unknown_node_type", "x")) == 404
    assert neighborhood_error_http_status(OntologyNeighborhoodError("dangling_endpoint", "x")) == 404
    assert neighborhood_error_http_status(OntologyNeighborhoodError("invalid_focus_id", "x")) == 422
    assert neighborhood_error_http_status(OntologyNeighborhoodError("unbounded_request", "x")) == 422
    assert neighborhood_error_http_status(OntologyNeighborhoodError("stale_snapshot", "x")) == 422


def test_neighborhood_error_detail_hides_focus_existence() -> None:
    for code in ("focus_hidden", "focus_not_visible", "unknown_node_type", "dangling_endpoint"):
        assert neighborhood_error_detail(OntologyNeighborhoodError(code, "catalog-secret")) == (
            "focus node is unavailable"
        )
    assert neighborhood_error_detail(OntologyNeighborhoodError("invalid_focus_id", "malformed")) == (
        "malformed"
    )


def test_focus_catalog_exists_rejects_unknown_and_non_uuid() -> None:
    conn = ScriptedConn({})
    assert asyncio.run(focus_catalog_exists(conn, NODE_POST, "not-a-uuid")) is False
    with pytest.raises(OntologyNeighborhoodError) as raised:
        asyncio.run(focus_catalog_exists(conn, "node_invented", POST_ID))
    assert raised.value.code == "unknown_node_type"
    assert asyncio.run(
        focus_catalog_exists(
            ScriptedConn({"select 1 from source_post": {"ignored": 1}}), NODE_POST, POST_ID
        )
    )
    assert asyncio.run(
        focus_catalog_exists(
            ScriptedConn({"select 1 from cataloged_person": {"ignored": 1}}), NODE_PERSON, PERSON_ID
        )
    )
    assert asyncio.run(
        focus_catalog_exists(
            ScriptedConn({"select 1 from corporate_entity": {"ignored": 1}}),
            NODE_CORPORATE_ENTITY,
            CORP_ID,
        )
    )
    assert asyncio.run(
        focus_catalog_exists(
            ScriptedConn({"select 1 from cataloged_team": {"ignored": 1}}), NODE_TEAM, TEAM_ID
        )
    )
    assert asyncio.run(
        focus_catalog_exists(
            ScriptedConn({"from post_project_mention": {"ignored": 1}}),
            NODE_PROJECT,
            PROJECT_ID,
        )
    )
    empty = ScriptedConn({})
    assert asyncio.run(focus_catalog_exists(empty, NODE_PERSON, PERSON_ID)) is False
    assert asyncio.run(focus_catalog_exists(empty, NODE_CORPORATE_ENTITY, CORP_ID)) is False
    assert asyncio.run(focus_catalog_exists(empty, NODE_TEAM, TEAM_ID)) is False
    assert asyncio.run(focus_catalog_exists(empty, NODE_POST, POST_ID)) is False
    assert asyncio.run(focus_catalog_exists(empty, NODE_PROJECT, PROJECT_ID)) is False


def test_visible_post_ids_for_each_focus_type() -> None:
    post_row = {"post_id": POST_ID, "visibility_code": "public", "corporate_entity_id": CORP_ID}
    conn = ScriptedConn({"select post_id, visibility_code": post_row})
    assert asyncio.run(visible_post_ids_for_focus(conn, NODE_POST, POST_ID, lambda row: True)) == [POST_ID]
    assert asyncio.run(visible_post_ids_for_focus(conn, NODE_POST, POST_ID, lambda row: False)) == []
    assert asyncio.run(visible_post_ids_for_focus(ScriptedConn({}), NODE_POST, POST_ID, lambda row: True)) == []
    assert asyncio.run(
        visible_post_ids_for_focus(
            ScriptedConn({"combined_post_person_mention": [post_row]}),
            NODE_PERSON,
            PERSON_ID,
            lambda row: True,
        )
    ) == [POST_ID]
    assert asyncio.run(
        visible_post_ids_for_focus(
            ScriptedConn({"from post_project_mention mention": [post_row]}),
            NODE_PROJECT,
            PROJECT_ID,
            lambda row: True,
        )
    ) == [POST_ID]
    assert asyncio.run(
        visible_post_ids_for_focus(
            ScriptedConn({"person_affiliation affiliation": [post_row]}),
            NODE_CORPORATE_ENTITY,
            CORP_ID,
            lambda row: True,
        )
    ) == [POST_ID]
    assert asyncio.run(
        visible_post_ids_for_focus(
            ScriptedConn({"post_team_mention": [post_row]}),
            NODE_TEAM,
            TEAM_ID,
            lambda row: True,
        )
    ) == [POST_ID]
    with pytest.raises(OntologyNeighborhoodError) as raised:
        asyncio.run(visible_post_ids_for_focus(conn, "node_invented", POST_ID, lambda row: True))
    assert raised.value.code == "unknown_node_type"


def test_load_facts_skos_and_labels() -> None:
    assert asyncio.run(_load_facts(ScriptedConn({}), [])) == []
    assert asyncio.run(_load_skos_facts(ScriptedConn({}), [])) == []
    conn = ScriptedConn(
        {
            "from knowledge_graph_edge edge": [
                {
                    "source_node_type_code": NODE_PERSON,
                    "source_node_id": PERSON_ID,
                    "target_node_type_code": NODE_POST,
                    "target_node_id": POST_ID,
                    "edge_type_code": EDGE_MENTION,
                    "available_at": T0,
                    "evidence_ids": [POST_ID],
                },
                {
                    "source_node_type_code": NODE_PERSON,
                    "source_node_id": PERSON_ID,
                    "target_node_type_code": NODE_CORPORATE_ENTITY,
                    "target_node_id": CORP_ID,
                    "edge_type_code": EDGE_AFFILIATION,
                    "available_at": T0,
                    "evidence_ids": None,
                },
                {
                    "source_node_type_code": NODE_POST,
                    "source_node_id": POST_ID,
                    "target_node_type_code": NODE_PROJECT,
                    "target_node_id": PROJECT_ID,
                    "edge_type_code": EDGE_MENTION_PROJECT,
                    "truth_status_code": "truth_proposed",
                    "available_at": T0,
                    "evidence_ids": [POST_ID],
                },
            ]
        }
    )
    facts = asyncio.run(_load_facts(conn, [POST_ID]))
    assert "with recursive" in conn.calls[0][0].lower()
    assert facts[0].property_code == "mentions"
    assert facts[0].source_node_id == POST_ID
    assert facts[1].evidence_references == ()
    assert facts[2].target_node_type_code == NODE_PROJECT
    assert facts[2].truth_status_code == "truth_proposed"
    assert facts[2].provenance_reference == "post_project_mention"
    skos = asyncio.run(
        _load_skos_facts(
            ScriptedConn(
                {
                    "from corporate_entity": [
                        {
                            "corporate_entity_id": CORP_ID,
                            "parent_entity_id": GROUP_ID,
                            "created_at": T0,
                        }
                    ]
                }
            ),
            [CORP_ID],
        )
    )
    assert skos[0].target_node_id == GROUP_ID
    mention = fact_from_knowledge_graph_edge(
        source_node_type_code=NODE_PERSON,
        source_node_id=PERSON_ID,
        target_node_type_code=NODE_POST,
        target_node_id=POST_ID,
        edge_type_code=EDGE_MENTION,
        recorded_at=T0,
        evidence_references=(POST_ID,),
    )
    team_fact = fact_from_knowledge_graph_edge(
        source_node_type_code=NODE_TEAM,
        source_node_id=TEAM_ID,
        target_node_type_code=NODE_POST,
        target_node_id=POST_ID,
        edge_type_code="edge_mention_team",
        recorded_at=T0,
    )
    affiliation = fact_from_knowledge_graph_edge(
        source_node_type_code=NODE_PERSON,
        source_node_id=PERSON_ID,
        target_node_type_code=NODE_CORPORATE_ENTITY,
        target_node_id=CORP_ID,
        edge_type_code=EDGE_AFFILIATION,
        recorded_at=T0,
    )
    project_fact = fact_from_knowledge_graph_edge(
        source_node_type_code=NODE_POST,
        source_node_id=POST_ID,
        target_node_type_code=NODE_PROJECT,
        target_node_id=PROJECT_ID,
        edge_type_code=EDGE_MENTION_PROJECT,
        recorded_at=T0,
        evidence_references=(POST_ID,),
    )
    labels = asyncio.run(
        _load_labels(
            ScriptedConn(
                {
                    "from cataloged_person": [{"person_id": PERSON_ID, "person_name": "Test Person"}],
                    "from source_post where post_id = any": [
                        {"post_id": POST_ID, "post_title": "Demo public post"}
                    ],
                    "from corporate_entity": [
                        {"corporate_entity_id": CORP_ID, "entity_name": "Demo Corp"}
                    ],
                    "from cataloged_team": [{"team_id": TEAM_ID, "team_name": "Demo Team"}],
                    "group by project_key": [
                        {"project_key": PROJECT_ID, "display_label": "Demo Project"}
                    ],
                }
            ),
            [mention, team_fact, affiliation, project_fact],
        )
    )
    assert labels[(NODE_PERSON, PERSON_ID)] == "Test Person"
    assert labels[(NODE_POST, POST_ID)] == "Demo public post"
    assert labels[(NODE_CORPORATE_ENTITY, CORP_ID)] == "Demo Corp"
    assert labels[(NODE_TEAM, TEAM_ID)] == "Demo Team"
    assert labels[(NODE_PROJECT, PROJECT_ID)] == "Demo Project"
    empty_labels = asyncio.run(_load_labels(ScriptedConn({}), []))
    assert empty_labels == {}


def test_load_facts_does_not_report_exact_hard_cap_as_truncated(monkeypatch) -> None:
    """Fetch one lookahead row even when the response is at its hard cap."""

    monkeypatch.setattr(
        "backend.app.ontology_neighborhood_ingestion.HARD_MAXIMUM_EDGES", 2
    )
    rows = [
        {
            "source_node_type_code": NODE_PERSON,
            "source_node_id": PERSON_ID,
            "target_node_type_code": NODE_POST,
            "target_node_id": POST_ID,
            "edge_type_code": EDGE_MENTION,
            "available_at": T0,
            "evidence_ids": [POST_ID],
        },
        {
            "source_node_type_code": NODE_PERSON,
            "source_node_id": PERSON_ID,
            "target_node_type_code": NODE_CORPORATE_ENTITY,
            "target_node_id": CORP_ID,
            "edge_type_code": EDGE_AFFILIATION,
            "available_at": T0,
            "evidence_ids": [POST_ID],
        },
    ]
    conn = ScriptedConn({"from knowledge_graph_edge edge": rows})

    window = asyncio.run(_load_facts(conn, [POST_ID], maximum_edges=2))

    assert len(window) == 2
    assert window.truncated is False
    assert conn.calls[0][1][4] == 3


def test_null_labels_are_not_returned_and_catalog_metadata_is_optional() -> None:
    fact = fact_from_knowledge_graph_edge(
        source_node_type_code=NODE_PERSON,
        source_node_id=PERSON_ID,
        target_node_type_code=NODE_POST,
        target_node_id=POST_ID,
        edge_type_code=EDGE_MENTION,
        recorded_at=T0,
    )
    labels = asyncio.run(
        _load_labels(
            ScriptedConn(
                {
                    "from cataloged_person": [{"person_id": PERSON_ID, "person_name": None}],
                    "from source_post where post_id": [{"post_id": POST_ID, "post_title": None}],
                }
            ),
            [fact],
        )
    )
    assert labels == {}
    affiliation = fact_from_knowledge_graph_edge(
        source_node_type_code=NODE_PERSON,
        source_node_id=PERSON_ID,
        target_node_type_code=NODE_CORPORATE_ENTITY,
        target_node_id=CORP_ID,
        edge_type_code=EDGE_AFFILIATION,
        recorded_at=T0,
    )
    team = fact_from_knowledge_graph_edge(
        source_node_type_code=NODE_TEAM,
        source_node_id=TEAM_ID,
        target_node_type_code=NODE_POST,
        target_node_id=POST_ID,
        edge_type_code="edge_mention_team",
        recorded_at=T0,
    )
    assert asyncio.run(
        _load_labels(
            ScriptedConn(
                {
                    "from corporate_entity": [{"corporate_entity_id": CORP_ID, "entity_name": None}],
                    "from cataloged_team": [{"team_id": TEAM_ID, "team_name": None}],
                }
            ),
            [affiliation, team],
        )
    ) == {}
    metadata = asyncio.run(
        _load_node_metadata(
            ScriptedConn(
                {
                    "select person_id, created_at": [{"person_id": PERSON_ID, "created_at": T0}],
                    "select post_id, created_at": [{"post_id": POST_ID, "created_at": T0}],
                }
            ),
            [fact],
            focus_node_type_code=NODE_PERSON,
            focus_node_id=PERSON_ID,
        )
    )
    assert metadata[(NODE_PERSON, PERSON_ID)].recorded_at == T0
    assert metadata[(NODE_PERSON, PERSON_ID)].truth_status_code is None


def test_visible_ontology_neighborhood_round_trips_and_payload() -> None:
    conn = ScriptedConn(
        {
            "select 1 from source_post": {"ignored": 1},
                "select post_id, visibility_code": {
                    "post_id": POST_ID,
                    "visibility_code": "visibility_public",
                    "corporate_entity_id": CORP_ID,
                },
                "select post.post_id, post.visibility_code": [
                    {
                        "post_id": POST_ID,
                        "visibility_code": "visibility_public",
                        "corporate_entity_id": CORP_ID,
                    }
                ],
                "select distinct post.post_id": [
                    {
                        "post_id": POST_ID,
                        "visibility_code": "visibility_public",
                        "corporate_entity_id": CORP_ID,
                    }
                ],
            "knowledge_graph_edge": [
                {
                    "source_node_type_code": NODE_PERSON,
                    "source_node_id": PERSON_ID,
                    "target_node_type_code": NODE_POST,
                    "target_node_id": POST_ID,
                    "edge_type_code": EDGE_MENTION,
                    "available_at": T0,
                    "evidence_ids": [POST_ID],
                },
                {
                    "source_node_type_code": NODE_PERSON,
                    "source_node_id": PERSON_ID,
                    "target_node_type_code": NODE_CORPORATE_ENTITY,
                    "target_node_id": CORP_ID,
                    "edge_type_code": EDGE_AFFILIATION,
                    "available_at": T0,
                    "evidence_ids": [POST_ID],
                },
            ],
            "select person_id, person_name": [{"person_id": PERSON_ID, "person_name": "Test Person"}],
            "select post_id, post_title": [
                {"post_id": POST_ID, "post_title": "Demo public post"}
            ],
            "select corporate_entity_id, entity_name": [
                {"corporate_entity_id": CORP_ID, "entity_name": "Demo Corp"}
            ],
            "select post_title from source_post": "Demo public post",
        }
    )
    neighborhood = asyncio.run(
        visible_ontology_neighborhood(
            conn,
            focus_node_type_code=NODE_POST,
            focus_node_id=POST_ID,
            can_see_post=lambda row: True,
            maximum_depth=2,
        )
    )
    payload = neighborhood_to_payload(neighborhood)
    assert payload["focus_node_id"] == POST_ID
    assert payload["truncated"] is False
    properties = {edge["property_code"] for edge in payload["edges"]}
    assert "mentions" in properties
    assert "affiliatedWith" in properties
    assert payload["edges"][0]["source_node_type_code"]
    assert payload["edges"][0]["target_node_type_code"]
    assert payload["jsonld"]["@graph"]
    assert payload["exact_value_rows"]
    assert all(node["shape_code"] for node in payload["nodes"])


def test_visible_neighborhood_drops_unlabeled_non_focus_edges() -> None:
    neighborhood = asyncio.run(
        visible_ontology_neighborhood(
            ScriptedConn(
                {
                    "select 1 from source_post": {"ignored": 1},
                    "select post_id, visibility_code": {
                        "post_id": POST_ID,
                        "visibility_code": "visibility_public",
                        "corporate_entity_id": CORP_ID,
                    },
                    "knowledge_graph_edge": [
                        {
                            "source_node_type_code": NODE_PERSON,
                            "source_node_id": PERSON_ID,
                            "target_node_type_code": NODE_POST,
                            "target_node_id": POST_ID,
                            "edge_type_code": EDGE_MENTION,
                            "available_at": T0,
                            "evidence_ids": [POST_ID],
                        }
                    ],
                    "select person_id, person_name": [],
                    "combined_post_person_mention": [],
                    "select post_id, post_title": [
                        {"post_id": POST_ID, "post_title": "Demo public post"}
                    ],
                    "select post_title from source_post": "Demo public post",
                }
            ),
            focus_node_type_code=NODE_POST,
            focus_node_id=POST_ID,
            can_see_post=lambda row: True,
        )
    )
    assert neighborhood.focus_node_id == POST_ID
    assert neighborhood.edges == ()
    assert neighborhood.limitation_code == "neighborhood_empty"


def test_visible_neighborhood_focus_variants_and_fail_closed() -> None:
    with pytest.raises(OntologyNeighborhoodError) as invalid:
        asyncio.run(
            visible_ontology_neighborhood(
                ScriptedConn({}),
                focus_node_type_code=NODE_POST,
                focus_node_id=" ",
                can_see_post=lambda row: True,
            )
        )
    assert invalid.value.code == "invalid_focus_id"
    with pytest.raises(OntologyNeighborhoodError) as noncanonical_project:
        asyncio.run(
            visible_ontology_neighborhood(
                ScriptedConn({}),
                focus_node_type_code=NODE_PROJECT,
                focus_node_id="Demo Project",
                can_see_post=lambda row: True,
            )
        )
    assert noncanonical_project.value.code == "invalid_focus_id"
    with pytest.raises(OntologyNeighborhoodError) as unknown:
        asyncio.run(
            visible_ontology_neighborhood(
                ScriptedConn({}),
                focus_node_type_code="node_invented",
                focus_node_id=POST_ID,
                can_see_post=lambda row: True,
            )
        )
    assert unknown.value.code == "unknown_node_type"
    with pytest.raises(OntologyNeighborhoodError) as missing:
        asyncio.run(
            visible_ontology_neighborhood(
                ScriptedConn({}),
                focus_node_type_code=NODE_POST,
                focus_node_id=POST_ID,
                can_see_post=lambda row: True,
            )
        )
    assert missing.value.code == "unknown_node_type"
    with pytest.raises(OntologyNeighborhoodError) as forbidden:
        asyncio.run(
            visible_ontology_neighborhood(
                ScriptedConn({"select 1 from source_post": {"ignored": 1}}),
                focus_node_type_code=NODE_POST,
                focus_node_id=POST_ID,
                can_see_post=lambda row: False,
            )
        )
    assert forbidden.value.code == "focus_not_visible"

    person_neighborhood = asyncio.run(
        visible_ontology_neighborhood(
            ScriptedConn(
                {
                    "select 1 from cataloged_person": {"ignored": 1},
                    "combined_post_person_mention": [
                        {
                            "post_id": POST_ID,
                            "visibility_code": "public",
                            "corporate_entity_id": CORP_ID,
                        }
                    ],
                    "select person_name from cataloged_person": "Test Person",
                }
            ),
            focus_node_type_code=NODE_PERSON,
            focus_node_id=PERSON_ID,
            can_see_post=lambda row: True,
        )
    )
    assert person_neighborhood.focus_node_id == PERSON_ID
    assert person_neighborhood.limitation_code == "neighborhood_empty"

    corp_neighborhood = asyncio.run(
        visible_ontology_neighborhood(
            ScriptedConn(
                {
                    "select 1 from corporate_entity": {"ignored": 1},
                    "person_affiliation affiliation": [
                        {
                            "post_id": POST_ID,
                            "visibility_code": "public",
                            "corporate_entity_id": CORP_ID,
                        }
                    ],
                    "parent_entity_id": [
                        {
                            "corporate_entity_id": CORP_ID,
                            "parent_entity_id": GROUP_ID,
                            "created_at": T0,
                        }
                    ],
                    "select corporate_entity_id, entity_name": [
                        {"corporate_entity_id": CORP_ID, "entity_name": "Demo Corp"},
                        {"corporate_entity_id": GROUP_ID, "entity_name": "Demo Group"},
                    ],
                    "select entity_name from corporate_entity": "Demo Corp",
                }
            ),
            focus_node_type_code=NODE_CORPORATE_ENTITY,
            focus_node_id=CORP_ID,
            can_see_post=lambda row: True,
        )
    )
    assert corp_neighborhood.focus_node_type_code == NODE_CORPORATE_ENTITY

    team_neighborhood = asyncio.run(
        visible_ontology_neighborhood(
            ScriptedConn(
                {
                    "select 1 from cataloged_team": {"ignored": 1},
                    "post_team_mention": [
                        {
                            "post_id": POST_ID,
                            "visibility_code": "public",
                            "corporate_entity_id": CORP_ID,
                        }
                    ],
                    "select team_name from cataloged_team": "Demo Team",
                }
            ),
            focus_node_type_code=NODE_TEAM,
            focus_node_id=TEAM_ID,
            can_see_post=lambda row: True,
        )
    )
    assert team_neighborhood.nodes[0].display_label == "Demo Team"

    project_conn = ScriptedConn(
        {
            "with recursive candidate_facts as ( select edge.source_node_type_code": [],
            "from post_project_mention": {"ignored": 1},
            "from post_project_mention mention": [
                {
                    "post_id": POST_ID,
                    "visibility_code": "public",
                    "corporate_entity_id": CORP_ID,
                }
            ],
        }
    )
    project_neighborhood = asyncio.run(
        visible_ontology_neighborhood(
            project_conn,
            focus_node_type_code=NODE_PROJECT,
            focus_node_id=PROJECT_ID,
            can_see_post=lambda row: True,
        )
    )
    assert project_neighborhood.nodes[0].display_label == PROJECT_ID
    assert all("cataloged_team" not in query for query, _args in project_conn.calls)


def test_hidden_non_focus_node_is_removed_before_label_loading() -> None:
    conn = ScriptedConn(
        {
            "select 1 from source_post": {"ignored": 1},
            "select post_id, visibility_code": {
                "post_id": POST_ID,
                "visibility_code": "visibility_public",
                "corporate_entity_id": CORP_ID,
            },
            "select post.post_id, post.visibility_code": [],
            "knowledge_graph_edge": [
                {
                    "source_node_type_code": NODE_PERSON,
                    "source_node_id": PERSON_ID,
                    "target_node_type_code": NODE_POST,
                    "target_node_id": POST_ID,
                    "edge_type_code": EDGE_MENTION,
                    "available_at": T0,
                    "evidence_ids": [POST_ID],
                }
            ],
            "select post_title from source_post": "Demo public post",
        }
    )
    neighborhood = asyncio.run(
        visible_ontology_neighborhood(
            conn,
            focus_node_type_code=NODE_POST,
            focus_node_id=POST_ID,
            can_see_post=lambda row: True,
        )
    )
    assert neighborhood.edges == ()
    assert [node.node_id for node in neighborhood.nodes] == [POST_ID]


def test_focus_label_fetch_may_be_empty_when_facts_already_labeled() -> None:
    mention_row = {
        "source_node_type_code": NODE_PERSON,
        "source_node_id": PERSON_ID,
        "target_node_type_code": NODE_POST,
        "target_node_id": POST_ID,
        "edge_type_code": EDGE_MENTION,
        "available_at": T0,
        "evidence_ids": [POST_ID],
    }
    affiliation_row = {
        "source_node_type_code": NODE_PERSON,
        "source_node_id": PERSON_ID,
        "target_node_type_code": NODE_CORPORATE_ENTITY,
        "target_node_id": CORP_ID,
        "edge_type_code": EDGE_AFFILIATION,
        "available_at": T0,
        "evidence_ids": [POST_ID],
    }
    team_row = {
        "source_node_type_code": NODE_TEAM,
        "source_node_id": TEAM_ID,
        "target_node_type_code": NODE_POST,
        "target_node_id": POST_ID,
        "edge_type_code": "edge_mention_team",
        "available_at": T0,
        "evidence_ids": [POST_ID],
    }
    post_row = {"post_id": POST_ID, "visibility_code": "public", "corporate_entity_id": CORP_ID}
    shared_labels = {
        "select person_id, person_name": [{"person_id": PERSON_ID, "person_name": "Test Person"}],
        "select post_id, post_title": [{"post_id": POST_ID, "post_title": "Demo public post"}],
        "select corporate_entity_id, entity_name": [
            {"corporate_entity_id": CORP_ID, "entity_name": "Demo Corp"}
        ],
        "select team_id, team_name": [{"team_id": TEAM_ID, "team_name": "Demo Team"}],
        "select post_title from source_post": None,
        "select person_name from cataloged_person": None,
        "select entity_name from corporate_entity": None,
        "select team_name from cataloged_team": None,
        "knowledge_graph_edge": [mention_row, affiliation_row, team_row],
            "select post_id, visibility_code": post_row,
            "select post.post_id, post.visibility_code": [post_row],
        "combined_post_person_mention": [post_row],
        "person_affiliation affiliation": [post_row],
        "post_team_mention": [post_row],
    }
    post_neighborhood = asyncio.run(
        visible_ontology_neighborhood(
            ScriptedConn({**shared_labels, "select 1 from source_post": {"ignored": 1}}),
            focus_node_type_code=NODE_POST,
            focus_node_id=POST_ID,
            can_see_post=lambda row: True,
        )
    )
    assert post_neighborhood.nodes[0].display_label == "Demo public post"
    person_neighborhood = asyncio.run(
        visible_ontology_neighborhood(
            ScriptedConn({**shared_labels, "select 1 from cataloged_person": {"ignored": 1}}),
            focus_node_type_code=NODE_PERSON,
            focus_node_id=PERSON_ID,
            can_see_post=lambda row: True,
        )
    )
    assert person_neighborhood.focus_node_id == PERSON_ID
    corp_neighborhood = asyncio.run(
        visible_ontology_neighborhood(
            ScriptedConn({**shared_labels, "select 1 from corporate_entity": {"ignored": 1}}),
            focus_node_type_code=NODE_CORPORATE_ENTITY,
            focus_node_id=CORP_ID,
            can_see_post=lambda row: True,
        )
    )
    assert corp_neighborhood.focus_node_id == CORP_ID
    team_neighborhood = asyncio.run(
        visible_ontology_neighborhood(
            ScriptedConn({**shared_labels, "select 1 from cataloged_team": {"ignored": 1}}),
            focus_node_type_code=NODE_TEAM,
            focus_node_id=TEAM_ID,
            can_see_post=lambda row: True,
        )
    )
    assert team_neighborhood.focus_node_id == TEAM_ID


def test_load_labels_ignores_unknown_node_types() -> None:
    unknown = NeighborhoodFact(
        source_node_type_code="node_invented",
        source_node_id=PERSON_ID,
        target_node_type_code=NODE_POST,
        target_node_id=POST_ID,
        property_code=PROPERTY_AFFILIATED_WITH,
        truth_status_code=TRUTH_OBSERVED,
        recorded_at=T0,
    )
    labels = asyncio.run(_load_labels(ScriptedConn({}), [unknown]))
    assert labels == {}


def test_payload_serializes_optional_validity() -> None:
    fact = NeighborhoodFact(
        source_node_type_code=NODE_PERSON,
        source_node_id=PERSON_ID,
        target_node_type_code=NODE_CORPORATE_ENTITY,
        target_node_id=CORP_ID,
        property_code=PROPERTY_AFFILIATED_WITH,
        truth_status_code=TRUTH_OBSERVED,
        recorded_at=T0,
        valid_from=T0,
        valid_to=T0,
        evidence_references=(POST_ID,),
        provenance_reference="knowledge_graph_edge",
    )
    neighborhood = assemble_ontology_neighborhood(
        focus_node_type_code=NODE_PERSON,
        focus_node_id=PERSON_ID,
        facts=[fact],
        labels={
            (NODE_PERSON, PERSON_ID): "Test Person",
            (NODE_CORPORATE_ENTITY, CORP_ID): "Demo Corp",
        },
        node_metadata={
            (NODE_PERSON, PERSON_ID): OntologyNodeMetadata(
                truth_status_code=TRUTH_OBSERVED,
                recorded_at=T0,
            )
        },
    )
    payload = neighborhood_to_payload(neighborhood)
    assert payload["edges"][0]["valid_from"] is not None
    assert payload["edges"][0]["valid_to"] is not None
    assert payload["nodes"][0]["truth_status_code"] == TRUTH_OBSERVED
    assert payload["nodes"][0]["valid_from"] is None
