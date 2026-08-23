"""Consume Valkey post-content wake-ups and persist derived evidence."""

from __future__ import annotations

import asyncio
import logging
import time
from collections.abc import Callable
from uuid import UUID

import asyncpg
import redis.asyncio as redis

from backend.app.config import load_settings
from backend.app.post_content_queue import (
    FAILED,
    POST_CONTENT_MAX_ATTEMPTS,
    POST_CONTENT_RETRY_INTERVAL,
    POST_CONTENT_STREAM_KEY,
    QUEUED,
    RUNNING,
    STALE_RUNNING_INTERVAL,
    SUCCEEDED,
    post_content_is_complete,
    republish_queued_post_content_jobs,
    source_body_sha256,
    transition_post_content_job,
)
from lineageweave.embedding_client import EmbeddingClient
from lineageweave.image_content import ImageContentClient
from lineageweave.llm_context import build_post_llm_metadata, use_llm_metadata
from lineageweave.post_content_normalization import normalize_post_body
from lineageweave.post_content_persistence import persist_post_content
from lineageweave.post_structure import PostStructureClient

_logger = logging.getLogger(__name__)
_RECOVERY_INTERVAL_SECONDS = 30.0
_WORKER_RESTART_DELAY_SECONDS = 1.0
_INCOMPLETE_FAILURE_CODE = "post_content_ingestion_incomplete"
_ATTEMPT_LIMIT_FAILURE_CODE = "post_content_ingestion_attempt_limit"
_UNEXPECTED_FAILURE_DETAIL = "post-content ingestion failed; retry is scheduled"


async def _stream_tail(client: redis.Redis) -> str:
    """Start after historical wake-ups; the normalized ledger drives recovery."""
    rows = await client.xrevrange(POST_CONTENT_STREAM_KEY, count=1)
    return str(rows[0][0]) if rows else "0-0"


async def _claim_job(
    pool: asyncpg.Pool,
    post_id: str,
    source_body_digest: str,
    *,
    embedding_model_code: str,
    require_structure: bool = False,
) -> dict[str, object] | None:
    async with pool.acquire() as conn:
        async with conn.transaction():
            row = await conn.fetchrow(
                """
                select p.*, j.source_body_sha256 as job_source_body_sha256,
                       j.status_code as job_status_code,
                       j.attempt_count as job_attempt_count,
                       (
                           select count(*)
                           from post_content_ingestion_job_status_event event
                           where event.post_id = j.post_id
                             and event.status_code = $3
                             and event.status_ordinal > coalesce(
                                 (
                                     select max(boundary.status_ordinal)
                                     from post_content_ingestion_job_status_event boundary
                                     where boundary.post_id = j.post_id
                                       and boundary.status_code = $4
                                       and boundary.failure_code is null
                                 ),
                                 -1
                             )
                       ) as job_cycle_attempt_count,
                       j.started_at as job_started_at,
                       j.queued_at as job_queued_at
                from post_content_ingestion_job j
                join source_post p on p.post_id = j.post_id
                where j.post_id = $1::uuid
                  and j.source_body_sha256 = $2
                  and coalesce(upper(btrim(p.source_detail_state_code)), '') <> 'W'
                for update of j, p
                """,
                post_id,
                source_body_digest,
                RUNNING,
                QUEUED,
            )
            if row is None:
                return None
            if str(row.get("source_detail_state_code") or "").strip().upper() == "W":
                return None
            raw_body = row["post_body"]
            if not isinstance(raw_body, str):
                return None
            if source_body_sha256(raw_body) != source_body_digest:
                return None
            status_code = str(row["job_status_code"])
            cycle_attempt_count = int(row["job_cycle_attempt_count"])
            if status_code == FAILED:
                return None
            if status_code == RUNNING and cycle_attempt_count >= POST_CONTENT_MAX_ATTEMPTS:
                await transition_post_content_job(
                    conn,
                    post_id,
                    FAILED,
                    failure_code=_ATTEMPT_LIMIT_FAILURE_CODE,
                    detail_text="post-content ingestion attempt limit was already reached",
                )
                return None
            if status_code == QUEUED and cycle_attempt_count >= POST_CONTENT_MAX_ATTEMPTS:
                await transition_post_content_job(
                    conn,
                    post_id,
                    FAILED,
                    failure_code=_ATTEMPT_LIMIT_FAILURE_CODE,
                    detail_text="post-content ingestion attempt limit was already reached",
                )
                return None
            if status_code == QUEUED and cycle_attempt_count > 0:
                retry_ready = await conn.fetchval(
                    "select now() >= $1::timestamptz + $2::interval",
                    row["job_queued_at"],
                    POST_CONTENT_RETRY_INTERVAL,
                )
                if not retry_ready:
                    return None
            if status_code == SUCCEEDED:
                content_complete = await post_content_is_complete(
                    conn,
                    post_id,
                    embedding_model_code=embedding_model_code,
                    require_structure=require_structure,
                )
                if content_complete:
                    return None
            if status_code == RUNNING and row["job_started_at"] is not None:
                stale = await conn.fetchval(
                    "select now() - $1::timestamptz > $2::interval",
                    row["job_started_at"],
                    STALE_RUNNING_INTERVAL,
                )
                if not stale:
                    return None
            claimed_attempt_count = int(
                await conn.fetchval(
                    """
                    update post_content_ingestion_job
                    set attempt_count = attempt_count + 1
                    where post_id = $1
                      and source_body_sha256 = $2
                    returning attempt_count
                    """,
                    post_id,
                    source_body_digest,
                )
            )
            await transition_post_content_job(
                conn,
                post_id,
                RUNNING,
                expected_attempt_count=claimed_attempt_count,
                expected_source_body_sha256=source_body_digest,
            )
            claimed = dict(row)
            claimed["job_attempt_count"] = claimed_attempt_count
            claimed["job_cycle_attempt_count"] = cycle_attempt_count + 1
            return claimed


async def _lock_current_claim(
    conn: asyncpg.Connection,
    post_id: str,
    *,
    expected_source_body_sha256: str,
    expected_attempt_count: int,
) -> bool:
    """Lock and validate the immutable worker claim against current source."""
    row = await conn.fetchrow(
        """
        select post.post_body
        from post_content_ingestion_job job
        join source_post post on post.post_id = job.post_id
        where job.post_id = $1::uuid
          and job.source_body_sha256 = $2
          and job.attempt_count = $3
          and job.status_code = $4
        for update of job, post
        """,
        post_id,
        expected_source_body_sha256,
        expected_attempt_count,
        RUNNING,
    )
    if row is None:
        return False
    raw_body = row["post_body"]
    return isinstance(raw_body, str) and (
        source_body_sha256(raw_body) == expected_source_body_sha256
    )


async def _finish_job(
    pool: asyncpg.Pool,
    post_id: str,
    status_code: str,
    *,
    expected_source_body_sha256: str,
    expected_attempt_count: int,
    failure_code: str | None = None,
    detail_text: str | None = None,
) -> None:
    """Finish only the attempt that actually owns the running lease."""
    async with pool.acquire() as conn, conn.transaction():
        if not await _lock_current_claim(
            conn,
            post_id,
            expected_source_body_sha256=expected_source_body_sha256,
            expected_attempt_count=expected_attempt_count,
        ):
            return
        await transition_post_content_job(
            conn,
            post_id,
            status_code,
            expected_attempt_count=expected_attempt_count,
            expected_source_body_sha256=expected_source_body_sha256,
            expected_status_code=RUNNING,
            failure_code=failure_code,
            detail_text=detail_text,
        )


async def _finish_failed_job(
    pool: asyncpg.Pool,
    post_id: str,
    *,
    failure_code: str,
    detail_text: str,
    expected_source_body_sha256: str,
    expected_attempt_count: int,
    cycle_attempt_count: int,
) -> None:
    """Schedule one retry, or persist a terminal failure for this attempt.

    The running status and attempt number are locked before the transition so
    a worker whose lease was reclaimed cannot retry or terminally fail a newer
    attempt.
    """
    async with pool.acquire() as conn, conn.transaction():
        if not await _lock_current_claim(
            conn,
            post_id,
            expected_source_body_sha256=expected_source_body_sha256,
            expected_attempt_count=expected_attempt_count,
        ):
            return
        terminal = cycle_attempt_count >= POST_CONTENT_MAX_ATTEMPTS
        await transition_post_content_job(
            conn,
            post_id,
            FAILED if terminal else QUEUED,
            failure_code=_ATTEMPT_LIMIT_FAILURE_CODE if terminal else failure_code,
            detail_text=(
                "post-content ingestion reached its bounded retry limit"
                if terminal
                else detail_text
            ),
            expected_attempt_count=expected_attempt_count,
            expected_source_body_sha256=expected_source_body_sha256,
            expected_status_code=RUNNING,
        )


async def process_post_content_job(
    pool: asyncpg.Pool,
    *,
    post_id: str,
    source_body_digest: str,
    vision_factory: Callable[[], ImageContentClient],
    embedding_factory: Callable[[], EmbeddingClient],
    structure_factory: Callable[[], PostStructureClient],
) -> None:
    """Claim, process, and durably record one post-content ingestion job."""
    settings = load_settings()
    row = await _claim_job(
        pool,
        post_id,
        source_body_digest,
        embedding_model_code=settings.embedding_model,
        require_structure=bool(settings.orchestrator_base_url and settings.orchestrator_api_key),
    )
    if row is None:
        return
    attempt_count = int(row["job_attempt_count"])
    cycle_attempt_count = int(row["job_cycle_attempt_count"])
    try:
        raw_body = row["post_body"]
        if not isinstance(raw_body, str) or not raw_body.strip():
            raise ValueError("source post has no body")
        metadata = build_post_llm_metadata(post_id, row)
        embedding_client = embedding_factory()
        structure_client = structure_factory()
        with use_llm_metadata(metadata):
            vision_client = vision_factory()
            normalized = await asyncio.to_thread(normalize_post_body, raw_body, vision_client)
            async with pool.acquire() as conn:
                persisted_count = await persist_post_content(
                    conn,
                    post_id,
                    raw_body,
                    vision_client=vision_client,
                    embedding_client=embedding_client,
                    embedding_model_code=settings.embedding_model or None,
                    normalized_result=normalized,
                    structure_client=structure_client,
                    post_title=str(row["post_title"]),
                    expected_source_body_sha256=source_body_digest,
                    expected_attempt_count=attempt_count,
                )
            if persisted_count is None:
                return
            async with pool.acquire() as conn:
                complete = await post_content_is_complete(
                    conn,
                    post_id,
                    embedding_model_code=settings.embedding_model,
                    require_structure=bool(
                        settings.orchestrator_base_url and settings.orchestrator_api_key
                    ),
                )
            if not complete:
                await _finish_failed_job(
                    pool,
                    post_id,
                    failure_code=_INCOMPLETE_FAILURE_CODE,
                    detail_text="post-content providers did not produce complete persisted evidence",
                    expected_source_body_sha256=source_body_digest,
                    expected_attempt_count=attempt_count,
                    cycle_attempt_count=cycle_attempt_count,
                )
                return
    except Exception:
        _logger.exception("post content ingestion failed for post_id=%s", post_id)
        await _finish_failed_job(
            pool,
            post_id,
            failure_code="post_content_ingestion_failed",
            detail_text=_UNEXPECTED_FAILURE_DETAIL,
            expected_source_body_sha256=source_body_digest,
            expected_attempt_count=attempt_count,
            cycle_attempt_count=cycle_attempt_count,
        )
        return
    await _finish_job(
        pool,
        post_id,
        SUCCEEDED,
        expected_source_body_sha256=source_body_digest,
        expected_attempt_count=attempt_count,
    )


async def consume_post_content_stream_once(
    client: redis.Redis,
    pool: asyncpg.Pool,
    *,
    last_id: str,
    vision_factory: Callable[[], ImageContentClient],
    embedding_factory: Callable[[], EmbeddingClient],
    structure_factory: Callable[[], PostStructureClient],
) -> str:
    """Process one Valkey stream batch and return its last-seen cursor."""
    batches = await client.xread({POST_CONTENT_STREAM_KEY: last_id}, count=10, block=1000)
    for _stream_name, entries in batches:
        for entry_id, fields in entries:
            post_id = str(fields.get("post_id", "")).strip()
            digest = str(fields.get("source_body_sha256", "")).strip()
            try:
                UUID(post_id)
            except ValueError:
                post_id = ""
            if post_id and len(digest) == 64:
                await process_post_content_job(
                    pool,
                    post_id=post_id,
                    source_body_digest=digest,
                    vision_factory=vision_factory,
                    embedding_factory=embedding_factory,
                    structure_factory=structure_factory,
                )
            last_id = str(entry_id)
    return last_id


async def run_post_content_worker(
    client: redis.Redis,
    pool: asyncpg.Pool,
    *,
    vision_factory: Callable[[], ImageContentClient],
    embedding_factory: Callable[[], EmbeddingClient],
    structure_factory: Callable[[], PostStructureClient],
) -> None:
    """Run the at-least-once consumer and periodically recover queued rows."""
    last_id = await _stream_tail(client)
    last_recovery = 0.0
    while True:
        now = time.monotonic()
        if now - last_recovery >= _RECOVERY_INTERVAL_SECONDS:
            await republish_queued_post_content_jobs(client, pool)
            last_recovery = now
        last_id = await consume_post_content_stream_once(
            client,
            pool,
            last_id=last_id,
            vision_factory=vision_factory,
            embedding_factory=embedding_factory,
            structure_factory=structure_factory,
        )


async def run_post_content_worker_supervised(
    client: redis.Redis,
    pool: asyncpg.Pool,
    *,
    vision_factory: Callable[[], ImageContentClient],
    embedding_factory: Callable[[], EmbeddingClient],
    structure_factory: Callable[[], PostStructureClient],
) -> None:
    """Keep the durable worker alive after an unexpected iteration error.

    Cancellation remains a shutdown signal. Other exceptions are logged and
    the worker is restarted so a transient Valkey, database, or provider
    error cannot silently disable recovery for the rest of the process.
    """
    while True:
        try:
            await run_post_content_worker(
                client,
                pool,
                vision_factory=vision_factory,
                embedding_factory=embedding_factory,
                structure_factory=structure_factory,
            )
        except asyncio.CancelledError:
            raise
        except Exception:
            _logger.exception("post-content worker crashed; restarting")
            await asyncio.sleep(_WORKER_RESTART_DELAY_SECONDS)
