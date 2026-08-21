"""Regression tests for bounded ontology fact loading."""

from __future__ import annotations

import asyncio

from backend.app.ontology_neighborhood_ingestion import _load_facts
from lineageweave.knowledge_graph import NODE_POST
from lineageweave.ontology_neighborhood import HARD_MAXIMUM_EDGES


class _EmptyConnection:
    """Capture a bounded query without requiring a live PostgreSQL instance."""

    def __init__(self) -> None:
        self.query = ""
        self.arguments: tuple[object, ...] = ()

    async def fetch(self, query: str, *arguments: object) -> list[object]:
        self.query = query
        self.arguments = arguments
        return []


def test_load_facts_passes_the_request_edge_cap_to_sql() -> None:
    """Fact retrieval must be deterministic and bounded before assembly."""
    conn = _EmptyConnection()

    assert asyncio.run(_load_facts(conn, ["post-1"], maximum_edges=7)) == []

    normalized_query = " ".join(conn.query.lower().split())
    assert "with recursive candidate_facts" in normalized_query
    assert "order by candidate.edge_type_code" in normalized_query
    assert "limit $5::integer" in normalized_query
    assert conn.arguments[:3] == (["post-1"], NODE_POST, "")
    assert conn.arguments[4] == min(
        HARD_MAXIMUM_EDGES,
        7 * (conn.arguments[3] + 1) + 1,
    )
