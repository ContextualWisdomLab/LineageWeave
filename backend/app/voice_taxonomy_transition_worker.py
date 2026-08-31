"""Wake the Voice read projection at its persisted validity transition."""

from __future__ import annotations

import asyncio

import asyncpg

_CHANNEL = "voice_taxonomy_transition"


async def run_voice_taxonomy_transition_worker(database_url: str) -> None:
    """Reconcile due assertions without an arbitrary polling interval."""
    connection = await asyncpg.connect(
        database_url,
        server_settings={"jit": "off"},
    )
    wake = asyncio.Event()

    def notify(
        _connection: asyncpg.Connection,
        _process_id: int,
        _channel: str,
        _payload: str,
    ) -> None:
        """Wake the worker after a projection transition notification."""
        wake.set()

    await connection.add_listener(_CHANNEL, notify)
    try:
        while True:
            await connection.fetchval(
                "select reconcile_due_voice_taxonomy_read_projections()"
            )
            wake.clear()
            delay = await connection.fetchval(
                """
                select extract(epoch from
                    min(next_transition_at) - clock_timestamp())::double precision
                  from voice_taxonomy_post_read_projection
                 where next_transition_at is not null
                """
            )
            if delay is None:
                await wake.wait()
            elif delay <= 0:
                continue
            else:
                try:
                    await asyncio.wait_for(wake.wait(), timeout=delay)
                except TimeoutError:
                    pass
    finally:
        await connection.remove_listener(_CHANNEL, notify)
        await connection.close()
