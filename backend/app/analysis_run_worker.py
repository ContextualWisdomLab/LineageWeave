"""Consume durable analysis-run wake-ups from the Valkey stream.

PostgreSQL remains the source of truth. The worker only uses Valkey to wake
the existing idempotent delivery function; the account that created the run
supplies the internal visibility scope, and no event body is trusted.
"""

from __future__ import annotations

import asyncio
import logging
from uuid import UUID

import asyncpg
import redis.asyncio as redis

from backend.app.analysis_run_ingestion import AnalysisRunCreateError
from backend.app.analysis_run_outbox import OUTBOX_STREAM_KEY
from backend.app.analysis_run_start import deliver_queued_analysis_run
from lineageweave.adjudication_client import AdjudicationClient
from lineageweave.observability import traced
from lineageweave.tepp_client import TeppClient

_BROKER_RECOVERY_DELAY_SECONDS = 1.0
_worker_logger = logging.getLogger(__name__)


async def consume_analysis_run_stream_once(
    client: redis.Redis,
    pool: asyncpg.Pool,
    *,
    database_url: str,
    last_id: str,
    tepp_client: TeppClient,
    adjudication_client: AdjudicationClient,
) -> str:
    """Consume one batch and return the last inspected Valkey entry id.

    Invalid or stale entries are acknowledged by advancing the cursor; the
    durable PostgreSQL outbox remains available for a later explicit retry.
    """
    try:
        batches = await client.xread({OUTBOX_STREAM_KEY: last_id}, count=10, block=1000)
    except Exception:
        # Keep idle polls silent, but retain a diagnostic span for broker failures.
        with traced(
            "lineageweave.valkey.analysis_outbox_xread",
            {
                "db.system": "redis",
                "db.operation.name": "xread",
                "lineageweave.stream.kind": "analysis_outbox",
            },
        ):
            raise
    if not batches:
        return last_id
    with traced(
        "lineageweave.valkey.analysis_outbox_batch",
        {
            "db.system": "redis",
            "db.operation.name": "xread",
            "lineageweave.stream.kind": "analysis_outbox",
        },
    ):
        for _stream_name, entries in batches:
            for entry_id, fields in entries:
                analysis_run_id = str(fields.get("analysis_run_id", "")).strip()
                try:
                    UUID(analysis_run_id)
                except ValueError:
                    analysis_run_id = ""
                if analysis_run_id:
                    # One run's fail-closed refusal (404/409/503, e.g. channel
                    # weights not estimated yet, ADR 0145) must not end the
                    # worker task and halt every later run's delivery. The
                    # transaction rolls back, the durable outbox row stays
                    # available, and an explicit HTTP start retries the run
                    # once the operator resolves the named next action.
                    async with pool.acquire() as conn:
                        owner = await conn.fetchrow(
                            """
                            select requested_by_account_id
                            from analysis_run
                            where analysis_run_id = $1::uuid
                            """,
                            analysis_run_id,
                        )
                    if owner is not None:
                        try:
                            await deliver_queued_analysis_run(
                                pool,
                                database_url=database_url,
                                analysis_run_id=analysis_run_id,
                                account_id=str(owner["requested_by_account_id"]),
                                affiliated_entity_ids=[],
                                tepp_client=tepp_client,
                                adjudication_client=adjudication_client,
                                valkey_stream_entry_id=str(entry_id),
                            )
                        except AnalysisRunCreateError as exc:
                            _worker_logger.warning(
                                "analysis-run %s delivery refused (%s): %s",
                                analysis_run_id,
                                exc.status_code,
                                exc.detail,
                            )
                        except Exception as exc:
                            _worker_logger.warning(
                                "analysis-run %s delivery failed (error_type=%s)",
                                analysis_run_id,
                                type(exc).__name__,
                            )
                last_id = str(entry_id)
    return last_id


async def run_analysis_run_worker(
    client: redis.Redis,
    pool: asyncpg.Pool,
    *,
    database_url: str,
    tepp_client: TeppClient,
    adjudication_client: AdjudicationClient,
) -> None:
    """Run the single-process wake-up consumer until task cancellation."""
    last_id = "0-0"
    while True:
        try:
            last_id = await consume_analysis_run_stream_once(
                client,
                pool,
                last_id=last_id,
                database_url=database_url,
                tepp_client=tepp_client,
                adjudication_client=adjudication_client,
            )
        except (redis.RedisError, OSError) as exc:
            _worker_logger.warning(
                "analysis-run Valkey poll failed; retrying (error_type=%s)", type(exc).__name__
            )
            await asyncio.sleep(_BROKER_RECOVERY_DELAY_SECONDS)
