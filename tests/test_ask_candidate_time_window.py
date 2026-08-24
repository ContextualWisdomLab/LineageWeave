from __future__ import annotations

import asyncio
from datetime import date

from backend.app.post_chat_ingestion import gather_global_chat_sources


def test_candidate_query_receives_relative_event_window(monkeypatch) -> None:
    monkeypatch.setattr(
        "backend.app.post_chat_ingestion._seoul_today", lambda: date(2026, 8, 22)
    )
    calls: list[tuple[str, tuple[object, ...]]] = []

    class FakeConnection:
        async def fetch(self, query: str, *args):
            calls.append((query, args))
            return []

    asyncio.run(
        gather_global_chat_sources(
            FakeConnection(), lambda _row: True, question="어제 UAM", limit=4
        )
    )

    query, args = next((query, args) for query, args in calls if "matched_in" in query)
    assert args == ("uam", date(2026, 8, 21), date(2026, 8, 21))
    assert query.count("coalesce(event_occurred_at, created_at)") == 8
    assert query.count("$2::date is null") == 4
    assert query.count("$3::date is null") == 4
