"""Regression for replacing the current graph with an empty reconstruction."""

from __future__ import annotations

import asyncio
from typing import Any

from backend.app.lineage_ingestion import persist_lineage_edges


class _Connection:
    def __init__(self) -> None:
        self.calls: list[tuple[str, tuple[Any, ...]]] = []

    async def execute(self, query: str, *arguments: Any) -> str:
        self.calls.append((query, arguments))
        return "OK"


def test_empty_rebuild_creates_no_orphan_run_or_profile() -> None:
    connection = _Connection()

    asyncio.run(
        persist_lineage_edges(
            connection,
            [],
            channel_weights={"text": 1.0},
            reconstruction_version="empty-test-v1",
        )
    )

    assert connection.calls[0] == ("delete from post_lineage_edge", ())
    cleanup_query, cleanup_arguments = connection.calls[1]
    assert cleanup_query.startswith("delete from lineage_reconstruction_run old_run")
    assert "where not exists" in cleanup_query
    assert cleanup_arguments == ()
    assert len(connection.calls) == 2
    assert all(
        not query.startswith("insert into lineage_reconstruction_run ")
        for query, _ in connection.calls
    )
