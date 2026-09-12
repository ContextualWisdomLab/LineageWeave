from __future__ import annotations

import asyncio
from typing import Any

from backend.app.entity_relationship_ingestion import fetch_relationship_network


class RecordingConnection:
    def __init__(self) -> None:
        self.calls: list[tuple[str, tuple[Any, ...]]] = []

    async def fetch(self, sql: str, *args: Any) -> list[dict[str, Any]]:
        self.calls.append((sql, args))
        return []


def test_relationship_network_fails_closed_without_process_scope() -> None:
    conn = RecordingConnection()

    result = asyncio.run(fetch_relationship_network(conn, ["00000000-0000-0000-0000-000000000001"]))

    assert result == []
    scoped_sql, scoped_args = conn.calls[0]
    assert scoped_args == (["00000000-0000-0000-0000-000000000001"], None)
    assert "post.process_unit_id is null" in scoped_sql
    assert "$2::uuid[] is not null" in scoped_sql
    assert "post.process_unit_id = any($2::uuid[])" in scoped_sql


def test_relationship_network_binds_explicit_process_scope() -> None:
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
    )
