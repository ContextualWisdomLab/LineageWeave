"""Regression for atomic replacement of Event Lineage run evidence."""

from __future__ import annotations

import asyncio
from typing import Any

from backend.app.lineage_ingestion import persist_lineage_edges
from lineageweave.models import Edge


class _Connection:
    def __init__(self) -> None:
        self.calls: list[tuple[str, tuple[Any, ...]]] = []

    async def execute(self, query: str, *arguments: Any) -> str:
        self.calls.append((query, arguments))
        return "OK"


def test_rebuild_removes_superseded_unreferenced_run_profiles() -> None:
    connection = _Connection()
    edge = Edge(
        "11111111-1111-1111-1111-111111111111",
        "22222222-2222-2222-2222-222222222222",
        0.5,
        {"text": 0.5},
    )

    asyncio.run(
        persist_lineage_edges(
            connection,
            [edge],
            channel_weights={"text": 1.0},
            reconstruction_version="cleanup-test-v1",
        )
    )

    run_insert = next(
        arguments
        for query, arguments in connection.calls
        if "insert into lineage_reconstruction_run " in query
    )
    current_run_id = run_insert[0]
    cleanup = [
        (query, arguments)
        for query, arguments in connection.calls
        if "delete from lineage_reconstruction_run old_run" in query
    ]
    assert len(cleanup) == 1
    cleanup_query, cleanup_arguments = cleanup[0]
    assert cleanup_arguments == (current_run_id,)
    assert "old_run.lineage_reconstruction_run_id <> $1" in cleanup_query
    assert "not exists" in cleanup_query
    assert connection.calls[-1] == cleanup[0]
