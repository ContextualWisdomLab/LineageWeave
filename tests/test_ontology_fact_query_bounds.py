"""Regression tests for bounded ontology fact loading."""

from __future__ import annotations

import asyncio

from backend.app.ontology_neighborhood_ingestion import _load_facts


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
    assert "order by edge.edge_type_code, edge.source_node_id, edge.target_node_id" in normalized_query
    assert "limit $2" in normalized_query
    assert conn.arguments == (["post-1"], 7)
