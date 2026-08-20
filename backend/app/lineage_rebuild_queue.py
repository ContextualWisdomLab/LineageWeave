"""Durable Event Lineage rebuild jobs. PostgreSQL is truth; Valkey is a wake-up."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

import asyncpg
import redis.asyncio as redis

from lineageweave.adjudication_client import AdjudicationClient, NullAdjudicationClient
from lineageweave.models import Record
from lineageweave.reconstruct import DEFAULT_PAIR_LIMIT, estimate_candidate_pairs

LINEAGE_REBUILD_STREAM_KEY = "lineage-rebuild-outbox"
QUEUED = "lineage_rebuild_queued"
RUNNING = "lineage_rebuild_running"
SUCCEEDED = "lineage_rebuild_succeeded"
FAILED = "lineage_rebuild_failed"
CANCELLED = "lineage_rebuild_cancelled"
LLM_REQUESTED = "lineage_llm_requested"
LLM_AVAILABLE = "lineage_llm_available"
LLM_COMPLETED = "lineage_llm_completed"
LLM_SKIPPED = "lineage_llm_skipped"
LLM_FAILED = "lineage_llm_failed"
LLM_UNAVAILABLE = "lineage_llm_unavailable"
_ACTIVE = {QUEUED, RUNNING}

_INSERT_JOB_SQL = """
insert into lineage_rebuild_job (
    requested_by_account_id, source_snapshot_sha256, knowledge_cutoff,
    pair_estimate, pair_limit, llm_channel_requested, llm_channel_status_code,
    status_code
) values ($1::uuid, $2, $3, $4, $5, $6, $7, $8)
returning *
"""
_ACTIVE_JOB_SQL = """
select *
from lineage_rebuild_job
where source_snapshot_sha256 = $1
  and llm_channel_requested = $2
  and status_code = any($3::text[])
order by queued_at desc
limit 1
for update
"""
_JOB_BY_ID_SQL = """
select *
from lineage_rebuild_job
where lineage_rebuild_job_id = $1::uuid
"""
_EVENT_ORDINAL_SQL = """
select coalesce(max(status_ordinal), -1) + 1
from lineage_rebuild_job_status_event
where lineage_rebuild_job_id = $1::uuid
"""
_INSERT_EVENT_SQL = """
insert into lineage_rebuild_job_status_event (
    lineage_rebuild_job_id, status_ordinal, status_code,
    llm_channel_status_code, failure_code, detail_text
) values ($1::uuid, $2, $3, $4, $5, $6)
"""
_UPDATE_JOB_SQL = """
update lineage_rebuild_job
set status_code = $2,
    llm_channel_status_code = $3,
    attempt_count = $4,
    edge_count = $5,
    result_sha256 = $6,
    failure_code = $7,
    started_at = case when $2 = $8 then now() else started_at end,
    completed_at = case when $2 = any($9::text[]) then now() else completed_at end,
    updated_at = now()
where lineage_rebuild_job_id = $1::uuid
returning *
"""
_QUEUED_JOBS_SQL = """
select lineage_rebuild_job_id
from lineage_rebuild_job
where status_code = $1
order by queued_at
limit $2
"""


@dataclass(frozen=True)
class LineageRebuildEnqueue:
    """Result of inserting or reusing one rebuild job."""

    job: dict[str, Any]
    should_publish: bool


def source_snapshot_sha256(
    records: list[Record],
    *,
    llm_channel_requested: bool,
) -> str:
    """Hash identity clocks and grouping keys. Never hashes a post body."""
    material = json.dumps(
        {
            "llm_channel_requested": bool(llm_channel_requested),
            "records": [
                {
                    "group_key": record.group_key,
                    "occurred_at": record.occurred_at.isoformat(),
                    "record_id": record.record_id,
                    "secondary_key": record.secondary_key,
                }
                for record in sorted(records, key=lambda item: item.record_id)
            ],
        },
        separators=(",", ":"),
        sort_keys=True,
    )
    return hashlib.sha256(material.encode()).hexdigest()


def initial_llm_channel_status(
    *,
    llm_channel_requested: bool,
    llm_available: bool,
    pair_estimate: int,
    pair_limit: int,
) -> str:
    """Record requested / unavailable / skipped. Never invent a score."""
    if not llm_channel_requested:
        return LLM_SKIPPED
    if not llm_available:
        return LLM_UNAVAILABLE
    if pair_estimate > pair_limit:
        return LLM_SKIPPED
    return LLM_REQUESTED


def next_action_copy(*, status_code: str, llm_channel_status_code: str) -> str:
    """Buyer-facing next action. No TEPP theta is named."""
    if status_code == QUEUED:
        return "Rebuild is queued. Event Lineage updates when it succeeds."
    if status_code == RUNNING:
        if llm_channel_status_code in {LLM_REQUESTED, LLM_AVAILABLE}:
            return "Rebuild is using the LLM channel. Read Event Lineage after it succeeds."
        return "Rebuild is using the three-channel path. Read Event Lineage after it succeeds."
    if status_code == SUCCEEDED:
        if llm_channel_status_code == LLM_COMPLETED:
            return (
                "Rebuild succeeded with the LLM channel. "
                "Open Event Lineage to read the inferred links."
            )
        if llm_channel_status_code == LLM_SKIPPED:
            return (
                "Rebuild succeeded without the LLM channel. "
                "Open Event Lineage, or retry with a smaller corpus."
            )
        if llm_channel_status_code == LLM_UNAVAILABLE:
            return (
                "Rebuild succeeded on three channels. Open Event Lineage, "
                "then connect contextual-orchestrator to use the LLM channel."
            )
        if llm_channel_status_code == LLM_FAILED:
            return (
                "Rebuild succeeded on three channels after the LLM channel failed. "
                "Open Event Lineage, then retry when the orchestrator is healthy."
            )
        return "Rebuild succeeded. Open Event Lineage to read the inferred links."
    if status_code == FAILED:
        return "Rebuild failed. Retry rebuild. No LLM score was invented."
    if status_code == CANCELLED:
        return "Rebuild was cancelled. Queue a new rebuild to update Event Lineage."
    return "Read Event Lineage after rebuild succeeds."


def serialize_rebuild_job(row: Any) -> dict[str, Any]:
    """Typed API projection. Does not include post bodies or credentials."""
    status_code = str(row["status_code"])
    llm_status = str(row["llm_channel_status_code"])
    knowledge_cutoff = row["knowledge_cutoff"]
    if isinstance(knowledge_cutoff, datetime):
        cutoff_text = knowledge_cutoff.astimezone(timezone.utc).isoformat()
    else:
        cutoff_text = str(knowledge_cutoff)
    edge_count = row["edge_count"]
    return {
        "lineage_rebuild_job_id": str(row["lineage_rebuild_job_id"]),
        "status_code": status_code,
        "llm_channel_requested": bool(row["llm_channel_requested"]),
        "llm_channel_status_code": llm_status,
        "pair_estimate": int(row["pair_estimate"]),
        "pair_limit": int(row["pair_limit"]),
        "edge_count": None if edge_count is None else int(edge_count),
        "result_sha256": row["result_sha256"],
        "failure_code": row["failure_code"],
        "knowledge_cutoff": cutoff_text,
        "source_snapshot_sha256": str(row["source_snapshot_sha256"]),
        "next_action": next_action_copy(
            status_code=status_code,
            llm_channel_status_code=llm_status,
        ),
    }


def lineage_rebuild_stream_fields(*, lineage_rebuild_job_id: str) -> dict[str, str]:
    """Valkey carries only the job identity."""
    return {"lineage_rebuild_job_id": str(lineage_rebuild_job_id)}


async def publish_lineage_rebuild_event(
    client: redis.Redis | None,
    *,
    lineage_rebuild_job_id: str,
) -> str | None:
    """Wake the worker after the PostgreSQL transaction has committed."""
    if client is None:
        return None
    try:
        entry_id = await client.xadd(
            LINEAGE_REBUILD_STREAM_KEY,
            lineage_rebuild_stream_fields(
                lineage_rebuild_job_id=lineage_rebuild_job_id,
            ),
            maxlen=1000,
            approximate=True,
        )
    except redis.RedisError:
        return None
    return str(entry_id)


async def _record_status(
    conn: asyncpg.Connection,
    job_id: str,
    status_code: str,
    llm_channel_status_code: str,
    *,
    failure_code: str | None = None,
    detail_text: str | None = None,
) -> None:
    ordinal = await conn.fetchval(_EVENT_ORDINAL_SQL, job_id)
    await conn.execute(
        _INSERT_EVENT_SQL,
        job_id,
        int(ordinal),
        status_code,
        llm_channel_status_code,
        failure_code,
        detail_text,
    )


async def enqueue_lineage_rebuild(
    conn: asyncpg.Connection,
    *,
    account_id: str,
    records: list[Record],
    llm_channel_requested: bool,
    llm_available: bool,
    pair_limit: int = DEFAULT_PAIR_LIMIT,
    knowledge_cutoff: datetime | None = None,
) -> LineageRebuildEnqueue:
    """Insert or reuse an active job for this snapshot. Does not call an LLM."""
    digest = source_snapshot_sha256(
        records, llm_channel_requested=llm_channel_requested
    )
    pair_estimate = estimate_candidate_pairs(records)
    llm_status = initial_llm_channel_status(
        llm_channel_requested=llm_channel_requested,
        llm_available=llm_available,
        pair_estimate=pair_estimate,
        pair_limit=pair_limit,
    )
    cutoff = knowledge_cutoff or datetime.now(timezone.utc)
    if cutoff.tzinfo is None:
        cutoff = cutoff.replace(tzinfo=timezone.utc)
    existing = await conn.fetchrow(
        _ACTIVE_JOB_SQL,
        digest,
        llm_channel_requested,
        list(_ACTIVE),
    )
    if existing is not None:
        return LineageRebuildEnqueue(dict(existing), False)
    row = await conn.fetchrow(
        _INSERT_JOB_SQL,
        account_id,
        digest,
        cutoff,
        pair_estimate,
        pair_limit,
        llm_channel_requested,
        llm_status,
        QUEUED,
    )
    assert row is not None
    await _record_status(
        conn,
        str(row["lineage_rebuild_job_id"]),
        QUEUED,
        llm_status,
    )
    return LineageRebuildEnqueue(dict(row), True)


async def load_lineage_rebuild_job(
    conn: asyncpg.Connection,
    lineage_rebuild_job_id: str,
) -> dict[str, Any] | None:
    """Return one job row or None."""
    try:
        UUID(str(lineage_rebuild_job_id))
    except ValueError:
        return None
    row = await conn.fetchrow(_JOB_BY_ID_SQL, lineage_rebuild_job_id)
    return None if row is None else dict(row)


async def transition_lineage_rebuild_job(
    conn: asyncpg.Connection,
    lineage_rebuild_job_id: str,
    status_code: str,
    llm_channel_status_code: str,
    *,
    attempt_count: int | None = None,
    edge_count: int | None = None,
    result_sha256: str | None = None,
    failure_code: str | None = None,
    detail_text: str | None = None,
) -> dict[str, Any]:
    """Update the job and append its lifecycle event atomically."""
    current = await conn.fetchrow(_JOB_BY_ID_SQL, lineage_rebuild_job_id)
    if current is None:
        raise LookupError("lineage_rebuild_job_missing")
    next_attempt = (
        int(current["attempt_count"]) if attempt_count is None else attempt_count
    )
    row = await conn.fetchrow(
        _UPDATE_JOB_SQL,
        lineage_rebuild_job_id,
        status_code,
        llm_channel_status_code,
        next_attempt,
        edge_count if edge_count is not None else current["edge_count"],
        result_sha256 if result_sha256 is not None else current["result_sha256"],
        failure_code,
        RUNNING,
        [SUCCEEDED, FAILED, CANCELLED],
    )
    assert row is not None
    await _record_status(
        conn,
        lineage_rebuild_job_id,
        status_code,
        llm_channel_status_code,
        failure_code=failure_code,
        detail_text=detail_text,
    )
    return dict(row)


async def cancel_lineage_rebuild_job(
    conn: asyncpg.Connection,
    lineage_rebuild_job_id: str,
) -> dict[str, Any] | None:
    """Cancel a queued job. Running work is not interrupted mid-persist."""
    row = await conn.fetchrow(
        """
        select * from lineage_rebuild_job
        where lineage_rebuild_job_id = $1::uuid
        for update
        """,
        lineage_rebuild_job_id,
    )
    if row is None:
        return None
    if str(row["status_code"]) != QUEUED:
        return dict(row)
    return await transition_lineage_rebuild_job(
        conn,
        lineage_rebuild_job_id,
        CANCELLED,
        str(row["llm_channel_status_code"]),
        failure_code="lineage_rebuild_cancelled",
    )


async def republish_queued_lineage_rebuild_jobs(
    client: redis.Redis,
    pool: asyncpg.Pool,
    *,
    limit: int = 100,
) -> int:
    """Recover queued rows when Valkey was unavailable or its stream was lost."""
    async with pool.acquire() as conn:
        rows = await conn.fetch(_QUEUED_JOBS_SQL, QUEUED, limit)
    published = 0
    for row in rows:
        if await publish_lineage_rebuild_event(
            client,
            lineage_rebuild_job_id=str(row["lineage_rebuild_job_id"]),
        ):
            published += 1
    return published


def adjudication_client_for_job(
    requested: AdjudicationClient | None,
    llm_channel_status_code: str,
) -> AdjudicationClient:
    """Use the live client only when the job still intends to run the LLM channel."""
    if llm_channel_status_code in {LLM_REQUESTED, LLM_AVAILABLE}:
        client = requested or NullAdjudicationClient()
        if getattr(client, "available", False):
            return client
    return NullAdjudicationClient()
