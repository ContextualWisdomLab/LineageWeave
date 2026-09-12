from __future__ import annotations

import asyncio
from typing import Any

from backend.app.entity_relationship_ingestion import fetch_relationship_network


class RecordingConnection:
    """Asyncpg-shaped connection that records relationship-network SQL binds."""

    def __init__(self) -> None:
        """Start with no captured database calls."""
        self.calls: list[tuple[str, tuple[Any, ...]]] = []

    async def fetch(self, sql: str, *args: Any) -> list[dict[str, Any]]:
        """Record the literal query and bound scope values without returning rows."""
        self.calls.append((sql, args))
        return []


def test_relationship_network_fails_closed_without_process_scope() -> None:
    """Omitted process scope must expose only public evidence."""
    conn = RecordingConnection()

    result = asyncio.run(fetch_relationship_network(conn, ["00000000-0000-0000-0000-000000000001"]))

    assert result == []
    scoped_sql, scoped_args = conn.calls[0]
    assert scoped_args == (["00000000-0000-0000-0000-000000000001"], [], False)
    assert "($3::boolean or post.visibility_code = 'public')" in scoped_sql
    assert "cardinality($2::text[]) = 0" in scoped_sql
    assert "post.process_unit_id::text = any($2::text[])" in scoped_sql


def test_relationship_network_binds_explicit_process_scope() -> None:
    """A non-empty authenticated process scope must be bound into the query."""
    conn = RecordingConnection()

    result = asyncio.run(
        fetch_relationship_network(
            conn,
            ["00000000-0000-0000-0000-000000000001"],
            ["00000000-0000-0000-0000-000000000010"],
        )
    )

    assert result == []
    _, scoped_args = conn.calls[0]
    assert scoped_args == (
        ["00000000-0000-0000-0000-000000000001"],
        ["00000000-0000-0000-0000-000000000010"],
        True,
    )


def test_relationship_network_preserves_explicit_unrestricted_process_scope() -> None:
    """An explicit empty collection retains unrestricted-process authenticated scope."""
    conn = RecordingConnection()

    result = asyncio.run(
        fetch_relationship_network(
            conn,
            ["00000000-0000-0000-0000-000000000001"],
            [],
        )
    )

    assert result == []
    _, scoped_args = conn.calls[0]
    assert scoped_args == (["00000000-0000-0000-0000-000000000001"], [], True)
