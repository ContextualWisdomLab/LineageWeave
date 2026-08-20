"""Consume Valkey lineage-rebuild wake-ups and persist one complete graph."""

from __future__ import annotations

import asyncio
import logging
import time
from collections.abc import Callable
from uuid import UUID

import asyncpg
import redis.asyncio as redis

from lineageweave.adjudication_client import AdjudicationClient, NullAdjudicationClient
from lineageweave.lineage_persistence import (
    LineageReconstructionSpec,
    lineage_reconstruction_spec,
)

from backend.app.analysis_run_start import reconstruction_result_digest
from backend.app.lineage_ingestion import persist_lineage_edges, records_from_source_posts
from backend.app.lineage_rebuild_queue import (
    CANCELLED,
    FAILED,
    LINEAGE_REBUILD_STREAM_KEY,
    LLM_AVAILABLE,
    LLM_COMPLETED,
    LLM_FAILED,
    LLM_REQUESTED,
    LLM_UNAVAILABLE,
    RUNNING,
    SUCCEEDED,
    adjudication_client_for_job,
    republish_queued_lineage_rebuild_jobs,
    transition_lineage_rebuild_job,
)
from backend.app.post_eligibility import SOURCE_POST_ELIGIBILITY_SQL

_logger = logging.getLogger(__name__)
_RECOVERY_INTERVAL_SECONDS = 30.0
_STALE_RUNNING_INTERVAL = "15 minutes"
_ELIGIBLE_POSTS_SQL = (
    "select post_id, post_title, voc_type_code, created_at, corporate_entity_id, "
    "process_unit_id, thread_group_key, secondary_grouping_key "
    f"from source_post where {SOURCE_POST_ELIGIBILITY_SQL.format(alias='source_post')}"
)
_CLAIM_SQL = """
select *
from lineage_rebuild_job
where lineage_rebuild_job_id = $1::uuid
for update
"""
_BUMP_ATTEMPT_SQL = """
update lineage_rebuild_job
set attempt_count = attempt_count + 1
where lineage_rebuild_job_id = $1::uuid
"""


async def _claim_job(
    pool: asyncpg.Pool,
    lineage_rebuild_job_id: str,
) -> asyncpg.Record | None:
    async with pool.acquire() as conn:
        async with conn.transaction():
            row = await conn.fetchrow(_CLAIM_SQL, lineage_rebuild_job_id)
            if row is None:
                return None
            status_code = str(row["status_code"])
            if status_code == SUCCEEDED:
                return None
            if status_code in {FAILED, CANCELLED}:
                return None
            if status_code == RUNNING and row["started_at"] is not None:
                stale = await conn.fetchval(
                    "select now() - $1 > $2::interval",
                    row["started_at"],
                    _STALE_RUNNING_INTERVAL,
                )
                if not stale:
                    return None
            llm_status = str(row["llm_channel_status_code"])
            if llm_status == LLM_REQUESTED:
                llm_status = LLM_AVAILABLE
            await conn.execute(_BUMP_ATTEMPT_SQL, lineage_rebuild_job_id)
            await transition_lineage_rebuild_job(
                conn,
                lineage_rebuild_job_id,
                RUNNING,
                llm_status,
                attempt_count=int(row["attempt_count"]) + 1,
            )
            claimed = await conn.fetchrow(_CLAIM_SQL, lineage_rebuild_job_id)
            return claimed


async def _load_eligible_records(pool: asyncpg.Pool):
    async with pool.acquire() as conn:
        rows = await conn.fetch(_ELIGIBLE_POSTS_SQL)
    return records_from_source_posts(rows)


def _reconstruct_spec(
    records, llm: AdjudicationClient
) -> LineageReconstructionSpec:
    """Reconstruct edges and retain the evidence contract for persistence."""
    return lineage_reconstruction_spec(records, llm=llm)


async def process_lineage_rebuild_job(
    pool: asyncpg.Pool,
    *,
    lineage_rebuild_job_id: str,
    adjudication_factory: Callable[[], AdjudicationClient],
) -> None:
    """Claim one job, reconstruct off the event loop, persist once."""
    claimed = await _claim_job(pool, lineage_rebuild_job_id)
    if claimed is None:
        return
    llm_status = str(claimed["llm_channel_status_code"])
    try:
        records = await _load_eligible_records(pool)
        live_client = adjudication_factory()
        selected = adjudication_client_for_job(live_client, llm_status)
        used_llm = bool(getattr(selected, "available", False))
        if llm_status in {LLM_REQUESTED, LLM_AVAILABLE} and not used_llm:
            llm_status = LLM_UNAVAILABLE
        try:
            spec = await asyncio.to_thread(_reconstruct_spec, records, selected)
            if used_llm:
                llm_status = LLM_COMPLETED
        except Exception:
            if used_llm:
                _logger.exception(
                    "lineage rebuild LLM channel failed for job_id=%s",
                    lineage_rebuild_job_id,
                )
                llm_status = LLM_FAILED
                spec = await asyncio.to_thread(
                    _reconstruct_spec, records, NullAdjudicationClient()
                )
            else:
                raise
        edges = list(spec.edges)
        digest = reconstruction_result_digest(edges)
        async with pool.acquire() as conn:
            async with conn.transaction():
                current = await conn.fetchrow(_CLAIM_SQL, lineage_rebuild_job_id)
                if current is None or str(current["status_code"]) == CANCELLED:
                    return
                await persist_lineage_edges(
                    conn,
                    edges,
                    channel_weights=spec.channel_weights,
                    reconstruction_version=spec.reconstruction_version,
                )
                await transition_lineage_rebuild_job(
                    conn,
                    lineage_rebuild_job_id,
                    SUCCEEDED,
                    llm_status,
                    edge_count=len(edges),
                    result_sha256=digest,
                )
    except Exception as exc:  # noqa: BLE001 - durable failure is recorded for retry.
        _logger.exception("lineage rebuild failed for job_id=%s", lineage_rebuild_job_id)
        async with pool.acquire() as conn:
            async with conn.transaction():
                await transition_lineage_rebuild_job(
                    conn,
                    lineage_rebuild_job_id,
                    FAILED,
                    LLM_FAILED if llm_status in {LLM_REQUESTED, LLM_AVAILABLE} else llm_status,
                    failure_code="lineage_rebuild_failed",
                    detail_text=str(exc)[:1000],
                )


async def consume_lineage_rebuild_stream_once(
    client: redis.Redis,
    pool: asyncpg.Pool,
    *,
    last_id: str,
    adjudication_factory: Callable[[], AdjudicationClient],
) -> str:
    batches = await client.xread({LINEAGE_REBUILD_STREAM_KEY: last_id}, count=10, block=1000)
    for _stream_name, entries in batches:
        for entry_id, fields in entries:
            job_id = str(fields.get("lineage_rebuild_job_id", "")).strip()
            try:
                UUID(job_id)
            except ValueError:
                job_id = ""
            if job_id:
                await process_lineage_rebuild_job(
                    pool,
                    lineage_rebuild_job_id=job_id,
                    adjudication_factory=adjudication_factory,
                )
            last_id = str(entry_id)
    return last_id


async def run_lineage_rebuild_worker(
    client: redis.Redis,
    pool: asyncpg.Pool,
    *,
    adjudication_factory: Callable[[], AdjudicationClient],
) -> None:
    """Run the at-least-once consumer and periodically recover queued rows."""
    last_id = "0-0"
    last_recovery = 0.0
    while True:
        now = time.monotonic()
        if now - last_recovery >= _RECOVERY_INTERVAL_SECONDS:
            await republish_queued_lineage_rebuild_jobs(client, pool)
            last_recovery = now
        last_id = await consume_lineage_rebuild_stream_once(
            client,
            pool,
            last_id=last_id,
            adjudication_factory=adjudication_factory,
        )
