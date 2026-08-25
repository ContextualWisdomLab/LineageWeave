"""Batched endpoint-visibility and depth-expansion regressions."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from typing import Any

import backend.app.ontology_neighborhood_ingestion as ingestion
from lineageweave.knowledge_graph import (
    EDGE_AFFILIATION,
    EDGE_MENTION,
    NODE_CORPORATE_ENTITY,
    NODE_PERSON,
    NODE_POST,
    NODE_TEAM,
)
from lineageweave.ontology_neighborhood import (
    PROPERTY_MENTIONS_TEAM,
    TRUTH_OBSERVED,
    NeighborhoodFact,
    fact_from_knowledge_graph_edge,
    skos_broader_fact,
)

POST_ID = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa1"
SECOND_POST_ID = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa2"
THIRD_POST_ID = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa3"
PERSON_ID = "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbb1"
CORP_ID = "cccccccc-cccc-cccc-cccc-ccccccccccc1"
TEAM_ID = "dddddddd-dddd-dddd-dddd-ddddddddddd1"
T0 = datetime(2026, 1, 10, 12, 0, tzinfo=UTC)


class BatchConnection:
    """Return deterministic visibility rows for four node categories."""

    def __init__(self) -> None:
        self.fetch_calls: list[str] = []
        self.fetch_ids: list[object] = []

    async def fetch(self, sql: str, ids: object = None, *_args: object) -> list[RecordLikeRow]:
        """Return a row keyed by the SQL category marker and bound ids."""
        normalized = " ".join(sql.split())
        self.fetch_calls.append(normalized)
        self.fetch_ids.append(ids)
        if "from source_post post" in normalized and "post.post_id as node_id" in normalized:
            assert ids == [POST_ID]
            return [_row(POST_ID, POST_ID)]
        if "from combined_post_person_mention mention" in normalized:
            assert ids == [PERSON_ID]
            return [_row(PERSON_ID, SECOND_POST_ID)]
        if "from post_team_mention mention" in normalized:
            assert ids == [TEAM_ID]
            return [_row(TEAM_ID, SECOND_POST_ID)]
        if "affiliation.affiliated_corporate_entity_id as node_id" in normalized:
            assert ids == [CORP_ID]
            return [_row(CORP_ID, SECOND_POST_ID)]
        raise AssertionError(f"unexpected batch query: {normalized}")


class RecordLikeRow:
    """Model asyncpg.Record's keyed access without inheriting from dict."""

    def __init__(self, values: dict[str, object]) -> None:
        self._values = values

    def __getitem__(self, key: str) -> object:
        return self._values[key]


def _row(node_id: str, post_id: str) -> RecordLikeRow:
    return RecordLikeRow(
        {
            "node_id": node_id,
            "post_id": post_id,
            "visibility_code": "public",
            "corporate_entity_id": None,
            "created_at": T0,
        }
    )


def test_endpoint_visibility_is_batched_by_node_type() -> None:
    """A wide neighborhood must not issue one query per endpoint."""
    conn = BatchConnection()
    keys = {
        (NODE_POST, POST_ID),
        (NODE_PERSON, PERSON_ID),
        (NODE_CORPORATE_ENTITY, CORP_ID),
        (NODE_TEAM, TEAM_ID),
    }

    visible = asyncio.run(
        ingestion._visible_post_ids_by_nodes(  # type: ignore[attr-defined]
            conn,  # type: ignore[arg-type]
            keys,
            lambda row: row["visibility_code"] == "public",
        )
    )

    assert len(conn.fetch_calls) == 4
    assert visible[(NODE_POST, POST_ID)] == [POST_ID]
    assert visible[(NODE_PERSON, PERSON_ID)] == [SECOND_POST_ID]
    assert visible[(NODE_CORPORATE_ENTITY, CORP_ID)] == [SECOND_POST_ID]
    assert visible[(NODE_TEAM, TEAM_ID)] == [SECOND_POST_ID]
    assert conn.fetch_ids == [[POST_ID], [PERSON_ID], [CORP_ID], [TEAM_ID]]


def test_visible_neighbor_evidence_keeps_final_depth_endpoint_authorized(monkeypatch: Any) -> None:
    """A final expansion cannot silently drop a newly discovered endpoint."""
    mention = fact_from_knowledge_graph_edge(
        source_node_type_code=NODE_PERSON,
        source_node_id=PERSON_ID,
        target_node_type_code=NODE_POST,
        target_node_id=POST_ID,
        edge_type_code=EDGE_MENTION,
        recorded_at=T0,
        evidence_references=(POST_ID,),
    )
    affiliation = fact_from_knowledge_graph_edge(
        source_node_type_code=NODE_PERSON,
        source_node_id=PERSON_ID,
        target_node_type_code=NODE_CORPORATE_ENTITY,
        target_node_id=CORP_ID,
        edge_type_code=EDGE_AFFILIATION,
        recorded_at=T0,
        evidence_references=(SECOND_POST_ID,),
    )
    final_depth_fact = NeighborhoodFact(
        source_node_type_code=NODE_PERSON,
        source_node_id=PERSON_ID,
        target_node_type_code=NODE_TEAM,
        target_node_id=TEAM_ID,
        property_code=PROPERTY_MENTIONS_TEAM,
        truth_status_code=TRUTH_OBSERVED,
        recorded_at=T0,
        evidence_references=(THIRD_POST_ID,),
    )
    fact_calls: list[tuple[str, ...]] = []

    async def fake_exists(*_args: object) -> bool:
        return True

    async def fake_focus_posts(*_args: object, **_kwargs: object) -> list[str]:
        return [POST_ID]

    async def fake_load_facts(
        _conn: object,
        post_ids: list[str],
        **_kwargs: object,
    ) -> ingestion._LoadedFactWindow:  # type: ignore[attr-defined]
        fact_calls.append(tuple(post_ids))
        facts = [mention]
        if SECOND_POST_ID in post_ids:
            facts.append(affiliation)
        if THIRD_POST_ID in post_ids:
            facts.append(final_depth_fact)
        return ingestion._LoadedFactWindow(facts)  # type: ignore[attr-defined]

    async def fake_visible_nodes(
        _conn: object,
        keys: set[tuple[str, str]],
        _can_see_post: object,
        **_kwargs: object,
    ) -> dict[tuple[str, str], list[str]]:
        return {
            key: [THIRD_POST_ID]
            if key in {
                (NODE_CORPORATE_ENTITY, CORP_ID),
                (NODE_TEAM, TEAM_ID),
            }
            else [SECOND_POST_ID]
            if key == (NODE_PERSON, PERSON_ID)
            else [POST_ID]
            for key in keys
        }

    async def fake_no_skos(*_args: object) -> list[object]:
        return []

    async def fake_labels(
        *_args: object, **_kwargs: object
    ) -> dict[tuple[str, str], str]:
        return {
            (NODE_POST, POST_ID): "Focus",
            (NODE_PERSON, PERSON_ID): "Person",
            (NODE_CORPORATE_ENTITY, CORP_ID): "Organization",
            (NODE_TEAM, TEAM_ID): "Team",
        }

    async def fake_metadata(*_args: object, **_kwargs: object) -> dict[object, object]:
        return {}

    class FocusConnection:
        async def fetchval(self, _sql: str, *_args: object) -> str:
            return "Focus"

    monkeypatch.setattr(ingestion, "focus_catalog_exists", fake_exists)
    monkeypatch.setattr(ingestion, "visible_post_ids_for_focus", fake_focus_posts)
    monkeypatch.setattr(ingestion, "_load_facts", fake_load_facts)
    monkeypatch.setattr(ingestion, "_visible_post_ids_by_nodes", fake_visible_nodes, raising=False)
    monkeypatch.setattr(ingestion, "_load_skos_facts", fake_no_skos)
    monkeypatch.setattr(ingestion, "_load_labels", fake_labels)
    monkeypatch.setattr(ingestion, "_load_node_metadata", fake_metadata)

    neighborhood = asyncio.run(
        ingestion.visible_ontology_neighborhood(
            FocusConnection(),  # type: ignore[arg-type]
            focus_node_type_code=NODE_POST,
            focus_node_id=POST_ID,
            can_see_post=lambda _row: True,
            maximum_depth=2,
        )
    )

    assert fact_calls == [
        (POST_ID,),
        (POST_ID, SECOND_POST_ID),
        (POST_ID, SECOND_POST_ID, THIRD_POST_ID),
    ]
    assert {edge.property_code for edge in neighborhood.edges} == {
        "mentions",
        "affiliatedWith",
        PROPERTY_MENTIONS_TEAM,
    }


GROUP_ID = "eeeeeeee-eeee-eeee-eeee-eeeeeeeeeee1"


def test_skos_parent_requires_own_visible_post_evidence(monkeypatch: Any) -> None:
    """A visible child must not reveal a parent that has no authorized post."""
    affiliation = fact_from_knowledge_graph_edge(
        source_node_type_code=NODE_PERSON,
        source_node_id=PERSON_ID,
        target_node_type_code=NODE_CORPORATE_ENTITY,
        target_node_id=CORP_ID,
        edge_type_code=EDGE_AFFILIATION,
        recorded_at=T0,
        evidence_references=(POST_ID,),
    )
    parent_queries: list[set[tuple[str, str]]] = []

    async def fake_exists(*_args: object) -> bool:
        return True

    async def fake_focus_posts(*_args: object, **_kwargs: object) -> list[str]:
        return [POST_ID]

    async def fake_load_facts(*_args: object, **_kwargs: object) -> ingestion._LoadedFactWindow:
        return ingestion._LoadedFactWindow([affiliation])  # type: ignore[attr-defined]

    async def fake_visible_nodes(
        _conn: object,
        keys: set[tuple[str, str]],
        _can_see_post: object,
        **_kwargs: object,
    ) -> dict[tuple[str, str], list[str]]:
        parent_queries.append(set(keys))
        return {
            key: ([POST_ID] if key != (NODE_CORPORATE_ENTITY, GROUP_ID) else [])
            for key in keys
        }

    async def fake_skos(*_args: object) -> list[object]:
        return [
            skos_broader_fact(
                narrower_entity_id=CORP_ID,
                broader_entity_id=GROUP_ID,
                recorded_at=T0,
            )
        ]

    async def fake_labels(
        *_args: object, **_kwargs: object
    ) -> dict[tuple[str, str], str]:
        return {
            (NODE_POST, POST_ID): "Focus",
            (NODE_PERSON, PERSON_ID): "Person",
            (NODE_CORPORATE_ENTITY, CORP_ID): "Plant",
            (NODE_CORPORATE_ENTITY, GROUP_ID): "Hidden Group",
        }

    async def fake_metadata(*_args: object, **_kwargs: object) -> dict[object, object]:
        return {}

    class FocusConnection:
        async def fetchval(self, _sql: str, *_args: object) -> str:
            return "Plant"

    monkeypatch.setattr(ingestion, "focus_catalog_exists", fake_exists)
    monkeypatch.setattr(ingestion, "visible_post_ids_for_focus", fake_focus_posts)
    monkeypatch.setattr(ingestion, "_load_facts", fake_load_facts)
    monkeypatch.setattr(ingestion, "_visible_post_ids_by_nodes", fake_visible_nodes, raising=False)
    monkeypatch.setattr(ingestion, "_load_skos_facts", fake_skos)
    monkeypatch.setattr(ingestion, "_load_labels", fake_labels)
    monkeypatch.setattr(ingestion, "_load_node_metadata", fake_metadata)

    neighborhood = asyncio.run(
        ingestion.visible_ontology_neighborhood(
            FocusConnection(),  # type: ignore[arg-type]
            focus_node_type_code=NODE_CORPORATE_ENTITY,
            focus_node_id=CORP_ID,
            can_see_post=lambda _row: True,
            maximum_depth=2,
        )
    )

    assert any((NODE_CORPORATE_ENTITY, GROUP_ID) in keys for keys in parent_queries)
    assert all(edge.property_code != "skos_broader" for edge in neighborhood.edges)
    assert all(node.node_id != GROUP_ID for node in neighborhood.nodes)
