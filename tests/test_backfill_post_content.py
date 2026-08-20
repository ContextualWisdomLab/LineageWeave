"""Operator backfill connection recovery contracts."""

from __future__ import annotations

import asyncio

from scripts import backfill_post_content


def test_reconnects_only_after_database_connection_closes(monkeypatch) -> None:
    replacement_connection = object()
    connected_dsns: list[str] = []

    class Connection:
        def __init__(self, closed: bool) -> None:
            self._closed = closed

        def is_closed(self) -> bool:
            return self._closed

    async def connect(dsn: str):
        connected_dsns.append(dsn)
        return replacement_connection

    monkeypatch.setattr(backfill_post_content.asyncpg, "connect", connect)

    current_connection = Connection(False)
    assert (
        asyncio.run(backfill_post_content._ensure_open_connection(current_connection, "dsn"))
        is current_connection
    )
    assert asyncio.run(backfill_post_content._ensure_open_connection(Connection(True), "dsn")) is replacement_connection
    assert connected_dsns == ["dsn"]
