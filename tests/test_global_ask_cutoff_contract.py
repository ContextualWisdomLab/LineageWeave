"""Regression contracts for the final Global Ask source query."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime

from backend.app.post_chat_ingestion import gather_global_chat_sources


CUTOFF = datetime(2026, 8, 20, 12, 0, tzinfo=UTC)
AUTHORIZED_ENTITY_ID = "00000000-0000-4000-8000-000000000001"


class _RecordingConnection:
    """Record query arguments while returning an empty authorized corpus."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, tuple[object, ...]]] = []

    async def fetch(self, query: str, *args: object):
        """Record one query call and return no rows."""

        self.calls.append((query, args))
        return []


def test_final_global_source_query_reuses_scope_and_binds_cutoff() -> None:
    """One-shot tenant scope and the cutoff survive into the final SQL call."""

    connection = _RecordingConnection()
    authorized_ids = (value for value in [AUTHORIZED_ENTITY_ID])

    result = asyncio.run(
        gather_global_chat_sources(
            connection,
            lambda _row: True,
            authorized_ids,
            question="",
            limit=2,
            knowledge_cutoff=CUTOFF,
        )
    )

    assert result == []
    final_calls = [
        (query, args)
        for query, args in connection.calls
        if "array_position($2::uuid[], post_id)" in query
    ]
    assert len(final_calls) == 1
    final_query, final_args = final_calls[0]
    assert "created_at <= $4" in final_query
    assert final_args == ([AUTHORIZED_ENTITY_ID], [], 2, CUTOFF)
