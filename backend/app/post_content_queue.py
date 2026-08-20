"""Durable post-content ingestion jobs with a Valkey wake-up stream."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Any

import asyncpg
import redis.asyncio as redis

POST_CONTENT_STREAM_KEY = "post-content-ingestion"
QUEUED = "post_content_ingestion_queued"
RUNNING = "post_content_ingestion_running"
SUCCEEDED = "post_content_ingestion_succeeded"
FAILED = "post_content_ingestion_failed"
_ACTIVE = {QUEUED, RUNNING}
POST_CONTENT_MAX_ATTEMPTS = 3
POST_CONTENT_RETRY_INTERVAL = "5 minutes"


@dataclass(frozen=True)
class PostContentJobRequest:
    post_id: str
    source_body_sha256: str
    status_code: str
    should_publish: bool


def source_body_sha256(body: str) -> str:
    """Hash the immutable source representation, never the derived content."""
    return hashlib.sha256(body.encode("utf-8")).hexdigest()


def post_content_api_status(status_code: str | None, *, content_present: bool) -> str:
    if status_code in _ACTIVE:
        return "processing"
    if status_code == FAILED:
        return "unavailable"
    if content_present:
        return "ready"
    return "unavailable"


def post_content_stream_fields(*, post_id: str, source_body_digest: str) -> dict[str, str]:
    """Valkey carries only the identity and digest needed to wake a worker."""
    return {"post_id": str(post_id), "source_body_sha256": source_body_digest}


async def publish_post_content_event(
    client: redis.Redis | None,
    *,
    post_id: str,
    source_body_digest: str,
) -> str | None:
    """Wake the worker after the PostgreSQL transaction has committed."""
    if client is None:
        return None
    try:
        entry_id = await client.xadd(
            POST_CONTENT_STREAM_KEY,
            post_content_stream_fields(
                post_id=post_id,
                source_body_digest=source_body_digest,
            ),
            maxlen=1000,
            approximate=True,
        )
    except redis.RedisError:
        return None
    return str(entry_id)


async def _record_status(
    conn: asyncpg.Connection,
    post_id: str,
    status_code: str,
    *,
    failure_code: str | None = None,
    detail_text: str | None = None,
) -> None:
    ordinal = await conn.fetchval(
        """
        select coalesce(max(status_ordinal), -1) + 1
        from post_content_ingestion_job_status_event
        where post_id = $1
        """,
        post_id,
    )
    await conn.execute(
        """
        insert into post_content_ingestion_job_status_event
            (post_id, status_ordinal, status_code, failure_code, detail_text)
        values ($1, $2, $3, $4, $5)
        """,
        post_id,
        int(ordinal),
        status_code,
        failure_code,
        detail_text,
    )


async def transition_post_content_job(
    conn: asyncpg.Connection,
    post_id: str,
    status_code: str,
    *,
    failure_code: str | None = None,
    detail_text: str | None = None,
) -> None:
    """Update the job and append its lifecycle event atomically."""
    await conn.execute(
        """
        update post_content_ingestion_job
        set status_code = $2,
            started_at = case
                when $2 = $3 then now()
                when $2 = $6 then null
                else started_at
            end,
            completed_at = case when $2 in ($4, $5) then now() else null end,
            queued_at = case when $2 = $6 then now() else queued_at end,
            updated_at = now(),
            last_error_code = $7,
            last_error_detail = $8
        where post_id = $1
        """,
        post_id,
        status_code,
        RUNNING,
        SUCCEEDED,
        FAILED,
        QUEUED,
        failure_code,
        detail_text,
    )
    await _record_status(
        conn,
        post_id,
        status_code,
        failure_code=failure_code,
        detail_text=detail_text,
    )


async def ensure_post_content_job(
    conn: asyncpg.Connection,
    post_id: str,
    body: str,
    *,
    content_present: bool,
) -> PostContentJobRequest:
    """Create or requeue the job for the current source-body digest."""
    digest = source_body_sha256(body)
    row = await conn.fetchrow(
        """
        select source_body_sha256, status_code
        from post_content_ingestion_job
        where post_id = $1
        for update
        """,
        post_id,
    )
    if row is None:
        initial_status = SUCCEEDED if content_present else QUEUED
        await conn.execute(
            """
            insert into post_content_ingestion_job
                (post_id, source_body_sha256, status_code)
            values ($1, $2, $3)
            """,
            post_id,
            digest,
            initial_status,
        )
        await _record_status(conn, post_id, initial_status)
        return PostContentJobRequest(
            post_id,
            digest,
            initial_status,
            initial_status == QUEUED,
        )

    status_code = str(row["status_code"])
    needs_requeue = (
        str(row["source_body_sha256"]) != digest
        or (status_code == SUCCEEDED and not content_present)
    )
    if needs_requeue:
        await conn.execute(
            """
            update post_content_ingestion_job
            set source_body_sha256 = $2,
                status_code = $3,
                attempt_count = 0,
                queued_at = now(),
                started_at = null,
                completed_at = null,
                updated_at = now(),
                last_error_code = null,
                last_error_detail = null
            where post_id = $1
            """,
            post_id,
            digest,
            QUEUED,
        )
        await _record_status(conn, post_id, QUEUED)
        status_code = QUEUED
    return PostContentJobRequest(
        post_id,
        digest,
        status_code,
        status_code == QUEUED,
    )


async def republish_queued_post_content_jobs(
    client: redis.Redis,
    pool: asyncpg.Pool,
    *,
    limit: int = 100,
) -> int:
    """Recover queued rows when Valkey was unavailable or its stream was lost."""
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            select post_id, source_body_sha256
            from post_content_ingestion_job
            where status_code = $1
              and (
                  attempt_count = 0
                  or queued_at <= now() - $2::interval
              )
            order by queued_at
            limit $3
            """,
            QUEUED,
            POST_CONTENT_RETRY_INTERVAL,
            limit,
        )
    published = 0
    for row in rows:
        if await publish_post_content_event(
            client,
            post_id=str(row["post_id"]),
            source_body_digest=str(row["source_body_sha256"]),
        ):
            published += 1
    return published


def serialize_job_row(row: Any) -> dict[str, Any]:
    """Small internal projection used by diagnostics and tests."""
    return {
        "post_id": str(row["post_id"]),
        "source_body_sha256": str(row["source_body_sha256"]),
        "status_code": str(row["status_code"]),
        "attempt_count": int(row["attempt_count"]),
    }
