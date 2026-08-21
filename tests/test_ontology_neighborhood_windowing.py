"""Bounded-window and proximity-first ontology pagination regressions."""

from __future__ import annotations

import asyncio
from dataclasses import replace
from datetime import datetime, timezone

from backend.app.ontology_neighborhood_ingestion import _load_facts
from lineageweave.knowledge_graph import (
    EDGE_AFFILIATION,
    EDGE_MENTION,
    NODE_CORPORATE_ENTITY,
    NODE_PERSON,
    NODE_POST,
)
from lineageweave.ontology_neighborhood import (
    PROPERTY_AFFILIATED_WITH,
    PROPERTY_MENTIONS,
    assemble_ontology_neighborhood,
    fact_from_knowledge_graph_edge,
)

POST_ID = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa1"
PERSON_ID = "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbb1"
CORP_ID = "cccccccc-cccc-cccc-cccc-ccccccccccc1"
T0 = datetime(2026, 1, 10, 12, 0, tzinfo=timezone.utc)


class WindowConnection:
    """Return one more row than the requested bounded fact window."""

    async def fetch(self, _sql: str, *_args: object) -> list[dict[str, object]]:
        """Return four deterministic rows for a three-row window."""
        return [
            {
                "source_node_type_code": NODE_POST,
                "source_node_id": POST_ID,
                "target_node_type_code": NODE_PERSON,
                "target_node_id": f"bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbb{index}",
                "edge_type_code": EDGE_MENTION,
                "available_at": T0,
                "evidence_ids": [POST_ID],
            }
            for index in range(1, 5)
        ]


def test_fact_window_reports_source_truncation_without_exceeding_bound() -> None:
    """One look-ahead row must expose a bounded-window limitation."""
    window = asyncio.run(
        _load_facts(
            WindowConnection(),  # type: ignore[arg-type]
            [POST_ID],
            focus_node_type_code=NODE_POST,
            focus_node_id=POST_ID,
            maximum_depth=1,
            maximum_edges=1,
        )
    )

    assert len(window) == 1
    assert window.truncated is True


def test_source_window_truncation_remains_visible_without_a_fake_cursor() -> None:
    """A bounded SQL window must never be reported as a complete graph."""
    fact = fact_from_knowledge_graph_edge(
        source_node_type_code=NODE_POST,
        source_node_id=POST_ID,
        target_node_type_code=NODE_PERSON,
        target_node_id=PERSON_ID,
        edge_type_code=EDGE_MENTION,
        recorded_at=T0,
        evidence_references=(POST_ID,),
    )

    neighborhood = assemble_ontology_neighborhood(
        focus_node_type_code=NODE_POST,
        focus_node_id=POST_ID,
        facts=[fact],
        labels={(NODE_POST, POST_ID): "Focus", (NODE_PERSON, PERSON_ID): "Person"},
        maximum_edges=10,
        source_truncated=True,
    )

    assert neighborhood.truncated is True
    assert neighborhood.next_cursor is None


def test_first_page_preserves_breadth_first_proximity_before_property_sort() -> None:
    """A one-edge first page must stay connected to the focus node."""
    focus_edge = fact_from_knowledge_graph_edge(
        source_node_type_code=NODE_POST,
        source_node_id=POST_ID,
        target_node_type_code=NODE_PERSON,
        target_node_id=PERSON_ID,
        edge_type_code=EDGE_MENTION,
        recorded_at=T0,
    )
    second_hop = fact_from_knowledge_graph_edge(
        source_node_type_code=NODE_PERSON,
        source_node_id=PERSON_ID,
        target_node_type_code=NODE_CORPORATE_ENTITY,
        target_node_id=CORP_ID,
        edge_type_code=EDGE_AFFILIATION,
        recorded_at=T0,
    )

    neighborhood = assemble_ontology_neighborhood(
        focus_node_type_code=NODE_POST,
        focus_node_id=POST_ID,
        facts=[second_hop, focus_edge],
        labels={
            (NODE_POST, POST_ID): "Focus",
            (NODE_PERSON, PERSON_ID): "Person",
            (NODE_CORPORATE_ENTITY, CORP_ID): "Organization",
        },
        maximum_depth=2,
        maximum_edges=1,
    )

    assert len(neighborhood.edges) == 1
    assert neighborhood.edges[0].property_code == PROPERTY_MENTIONS
    assert neighborhood.edges[0].property_code != PROPERTY_AFFILIATED_WITH


def test_source_page_keeps_sql_reachable_edges_without_focus_bridge() -> None:
    """A later source page may contain only a relation beyond the focus edge."""
    second_hop = replace(
        fact_from_knowledge_graph_edge(
            source_node_type_code=NODE_PERSON,
            source_node_id=PERSON_ID,
            target_node_type_code=NODE_CORPORATE_ENTITY,
            target_node_id=CORP_ID,
            edge_type_code=EDGE_AFFILIATION,
            recorded_at=T0,
        ),
        source_hop_depth=1,
    )

    neighborhood = assemble_ontology_neighborhood(
        focus_node_type_code=NODE_POST,
        focus_node_id=POST_ID,
        facts=[second_hop],
        labels={
            (NODE_POST, POST_ID): "Focus",
            (NODE_PERSON, PERSON_ID): "Person",
            (NODE_CORPORATE_ENTITY, CORP_ID): "Organization",
        },
        maximum_depth=2,
        maximum_edges=1,
        source_truncated=True,
    )

    assert len(neighborhood.edges) == 1
    assert neighborhood.edges[0].property_code == PROPERTY_AFFILIATED_WITH


class CapturingWindowConnection:
    """Record the keyset query without a live PostgreSQL instance."""

    def __init__(self) -> None:
        self.query = ""
        self.arguments: tuple[object, ...] = ()

    async def fetch(self, query: str, *arguments: object) -> list[object]:
        """Capture SQL and return no rows."""
        self.query = query
        self.arguments = arguments
        return []


def test_load_facts_uses_keyset_not_offset() -> None:
    """Source continuation must resume after the last SQL key, never OFFSET."""
    from lineageweave.ontology_source_cursor import OntologySourceKey

    conn = CapturingWindowConnection()
    after = OntologySourceKey(
        hop_depth=0,
        edge_type_code=EDGE_MENTION,
        source_node_type_code=NODE_POST,
        source_node_id=POST_ID,
        target_node_type_code=NODE_PERSON,
        target_node_id=PERSON_ID,
    )
    window = asyncio.run(
        _load_facts(
            conn,  # type: ignore[arg-type]
            [POST_ID],
            focus_node_type_code=NODE_POST,
            focus_node_id=POST_ID,
            maximum_depth=1,
            maximum_edges=1,
            after_key=after,
        )
    )
    normalized = " ".join(conn.query.lower().split())
    assert "offset" not in normalized
    assert "$8::integer is null" in normalized
    assert conn.arguments[7] == 0
    assert conn.arguments[8] == EDGE_MENTION
    assert conn.arguments[10] == POST_ID
    assert conn.arguments[12] == PERSON_ID
    assert window == []
