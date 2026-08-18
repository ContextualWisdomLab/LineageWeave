"""Consume durable analysis-run wake-ups from the Valkey stream.

PostgreSQL remains the source of truth. The worker only uses Valkey to wake
the existing idempotent delivery function; the account that created the run
supplies the internal visibility scope, and no event body is trusted.
"""

from __future__ import annotations

import asyncpg
import redis.asyncio as redis
from uuid import UUID

from lineageweave.tepp_client import TeppClient

from backend.app.analysis_run_outbox import OUTBOX_STREAM_KEY
from backend.app.analysis_run_start import deliver_queued_analysis_run


async def consume_analysis_run_stream_once(
    client: redis.Redis,
    pool: asyncpg.Pool,
    *,
    last_id: str,
    tepp_client: TeppClient,
) -> str:
    """Consume one batch and return the last inspected Valkey entry id.

    Invalid or stale entries are acknowledged by advancing the cursor; the
    durable PostgreSQL outbox remains available for a later explicit retry.
    """
    batches = await client.xread({OUTBOX_STREAM_KEY: last_id}, count=10, block=1000)
    for _stream_name, entries in batches:
        for entry_id, fields in entries:
            analysis_run_id = str(fields.get("analysis_run_id", "")).strip()
            try:
                UUID(analysis_run_id)
            except ValueError:
                analysis_run_id = ""
            if analysis_run_id:
                async with pool.acquire() as conn:
                    async with conn.transaction():
                        owner = await conn.fetchrow(
                            """
                            select requested_by_account_id
                            from analysis_run
                            where analysis_run_id = $1::uuid
                            """,
                            analysis_run_id,
                        )
                        if owner is not None:
                            await deliver_queued_analysis_run(
                                conn,
                                analysis_run_id=analysis_run_id,
                                account_id=str(owner["requested_by_account_id"]),
                                affiliated_entity_ids=[],
                                tepp_client=tepp_client,
                                valkey_stream_entry_id=str(entry_id),
                            )
            last_id = str(entry_id)
    return last_id


async def run_analysis_run_worker(
    client: redis.Redis,
    pool: asyncpg.Pool,
    *,
    tepp_client: TeppClient,
) -> None:
    """Run the single-process wake-up consumer until task cancellation."""
    last_id = "0-0"
    while True:
        last_id = await consume_analysis_run_stream_once(
            client,
            pool,
            last_id=last_id,
            tepp_client=tepp_client,
        )
