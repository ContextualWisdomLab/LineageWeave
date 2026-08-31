"""Tests for transition-instant Voice projection reconciliation."""

import asyncio

from backend.app import voice_taxonomy_transition_worker as worker


def test_transition_worker_waits_for_database_notification(monkeypatch) -> None:
    """No configured polling interval is used when no transition is pending."""

    class Connection:
        def __init__(self) -> None:
            self.listener = None
            self.delay_queries = 0
            self.closed = False

        async def add_listener(self, channel, listener) -> None:
            assert channel == "voice_taxonomy_transition"
            self.listener = listener

        async def fetchval(self, query: str):
            if "reconcile_due" in query:
                return 0
            self.delay_queries += 1
            return None

        async def remove_listener(self, channel, listener) -> None:
            assert channel == "voice_taxonomy_transition"
            assert listener is self.listener

        async def close(self) -> None:
            self.closed = True

    connection = Connection()

    async def connect(database_url: str, **kwargs):
        assert database_url == "postgresql://synthetic"
        assert kwargs == {"server_settings": {"jit": "off"}}
        return connection

    monkeypatch.setattr(worker.asyncpg, "connect", connect)

    async def exercise() -> None:
        task = asyncio.create_task(
            worker.run_voice_taxonomy_transition_worker("postgresql://synthetic")
        )
        while connection.listener is None or connection.delay_queries == 0:
            await asyncio.sleep(0)
        connection.listener(connection, 1, "voice_taxonomy_transition", "")
        while connection.delay_queries < 2:
            await asyncio.sleep(0)
        task.cancel()
        await asyncio.gather(task, return_exceptions=True)

    asyncio.run(exercise())
    assert connection.closed
