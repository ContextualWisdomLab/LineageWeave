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
    transition_post_content_job,
)
from backend.app.operations_case_ingestion import persist_operations_cases
from lineageweave.embedding_client import EmbeddingClient
from lineageweave.http_client import HttpClientError
from lineageweave.image_content import ImageContentClient
from lineageweave.llm_context import build_post_llm_metadata, use_llm_metadata
from lineageweave.observability import record_server_failure, traced
from lineageweave.operations_case_analysis import ContextualOrchestratorOperationsCaseAnalysisClient
from lineageweave.post_content_normalization import normalize_post_body
from lineageweave.post_content_persistence import persist_post_content
from lineageweave.post_structure import PostStructureClient

_logger = logging.getLogger(__name__)
_RECOVERY_INTERVAL_SECONDS = 30.0
_BROKER_RECOVERY_DELAY_SECONDS = 1.0
_INCOMPLETE_FAILURE_CODE = "post_content_ingestion_incomplete"
_ATTEMPT_LIMIT_FAILURE_CODE = "post_content_ingestion_attempt_limit"
_SOURCE_BODY_MISSING_FAILURE_CODE = "post_content_source_body_missing"
_UNEXPECTED_FAILURE_DETAIL = "post-content provider operation failed; retry the ingestion job"


async def _stream_tail(client: redis.Redis) -> str:
    """Start after historical wake-ups; the normalized ledger drives recovery."""
    with traced(
        "lineageweave.valkey.post_content_xrevrange",
        {
            "db.system": "redis",
            "db.operation.name": "xrevrange",
            "lineageweave.stream.kind": "post_content",
        },
    ):
        rows = await client.xrevrange(POST_CONTENT_STREAM_KEY, count=1)
    return str(rows[0][0]) if rows else "0-0"


async def _claim_job(
    pool: asyncpg.Pool,
    post_id: str,
    source_body_digest: str,
    *,
    require_embedding: bool,
    require_structure: bool = False,
) -> asyncpg.Record | None:
    async with pool.acquire() as conn:
        async with conn.transaction():
            row = await conn.fetchrow(
                """
                select p.*, j.source_body_sha256 as job_source_body_sha256,
                       j.status_code as job_status_code,
                       j.attempt_count as job_attempt_count,
                       j.started_at as job_started_at,
                       j.queued_at as job_queued_at
                from post_content_ingestion_job j
                join source_post p on p.post_id = j.post_id
                where j.post_id = $1::uuid
                  and j.source_body_sha256 = $2
                for update of j, p
                """,
                post_id,
                source_body_digest,
            )
            if row is None:
                return None
            status_code = str(row["job_status_code"])
            attempt_count = int(row["job_attempt_count"])
            if status_code == FAILED:
                return None
            if status_code == RUNNING and attempt_count >= POST_CONTENT_MAX_ATTEMPTS:
                await transition_post_content_job(
                    conn,
                    post_id,
                    FAILED,
                    failure_code=_ATTEMPT_LIMIT_FAILURE_CODE,
                    detail_text="post-content ingestion attempt limit was already reached",
                )
                return None
            if status_code == QUEUED and attempt_count >= POST_CONTENT_MAX_ATTEMPTS:
                await transition_post_content_job(
                    conn,
                    post_id,
                    FAILED,
                    failure_code=_ATTEMPT_LIMIT_FAILURE_CODE,
                    detail_text="post-content ingestion attempt limit was already reached",
                )
                return None
            if status_code == QUEUED and attempt_count > 0:
                retry_ready = await conn.fetchval(
                    "select now() >= $1 + $2::interval",
                    row["job_queued_at"],
                    POST_CONTENT_RETRY_INTERVAL,
                )
                if not retry_ready:
                    return None
            if status_code == SUCCEEDED:
                content_complete = await post_content_is_complete(
                    conn,
                    post_id,
                    require_embedding=require_embedding,
                    require_structure=require_structure,
                )
                case_complete = not require_structure or bool(
                    await conn.fetchval(
                        "select exists (select 1 from operations_case_analysis "
                        "where post_id = $1 and source_body_sha256 = $2)",
                        post_id,
                        source_body_digest,
                    )
                )
                if content_complete and case_complete:
                    return None
            if status_code == RUNNING and row["job_started_at"] is not None:
                stale = await conn.fetchval(
                    "select now() - $1 > $2::interval",
                    row["job_started_at"],
                    STALE_RUNNING_INTERVAL,
                )
                if not stale:
                    return None
            await conn.execute(
                """
                update post_content_ingestion_job
                set attempt_count = attempt_count + 1
                where post_id = $1
                """,
                post_id,
            )
            await transition_post_content_job(conn, post_id, RUNNING)
            return row


async def _finish_job(
    pool: asyncpg.Pool,
    post_id: str,
    status_code: str,
    *,
    expected_attempt_count: int,
    failure_code: str | None = None,
    detail_text: str | None = None,
) -> None:
    """Finish only the attempt that actually owns the running lease."""
    async with pool.acquire() as conn:
        async with conn.transaction():
            await transition_post_content_job(
                conn,
                post_id,
                status_code,
                expected_attempt_count=expected_attempt_count,
                failure_code=failure_code,
                detail_text=detail_text,
            )


async def _finish_failed_job(
    pool: asyncpg.Pool,
    post_id: str,
    *,
    failure_code: str,
    detail_text: str,
    expected_attempt_count: int,
) -> None:
    """Schedule one retry, or persist a terminal failure for this attempt.

    The running status and attempt number are locked before the transition so
    a worker whose lease was reclaimed cannot retry or terminally fail a newer
    attempt.
    """
    async with pool.acquire() as conn:
        async with conn.transaction():
            attempt_count = int(
                await conn.fetchval(
                    """
                    select attempt_count
                    from post_content_ingestion_job
                    where post_id = $1
                      and status_code = $2
                    for update
                    """,
                    post_id,
                    RUNNING,
                )
                or -1
            )
            if attempt_count != expected_attempt_count:
                return
            terminal = attempt_count >= POST_CONTENT_MAX_ATTEMPTS
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
    """Claim, run, and record the outcome of one post-content ingestion job.

    Claims the job for `post_id`/`source_body_digest` (a no-op if it is
    already claimed, stale, or superseded), normalizes and persists the
    post body through the given provider clients, then marks the job
    succeeded or durably failed for retry.
    """
    settings = load_settings()
    require_orchestrator_evidence = bool(
        settings.orchestrator_base_url and settings.orchestrator_api_key
    )
    row = await _claim_job(
        pool,
        post_id,
        source_body_digest,
        require_embedding=require_orchestrator_evidence,
        require_structure=require_orchestrator_evidence,
    )
    if row is None:
        return
    attempt_count = int(row["job_attempt_count"]) + 1
    raw_body = row["post_body"]
    if not isinstance(raw_body, str) or not raw_body.strip():
        _logger.warning(
            "post content ingestion skipped: source post has no body",
            extra={"post_id": post_id},
        )
        await _finish_job(
            pool,
            post_id,
            FAILED,
            failure_code=_SOURCE_BODY_MISSING_FAILURE_CODE,
            detail_text="source post has no body",
            expected_attempt_count=attempt_count,
        )
        return
    try:
        metadata = build_post_llm_metadata(post_id, row)
        embedding_client = embedding_factory()
        structure_client = structure_factory()
        with use_llm_metadata(metadata):
            vision_client = vision_factory()
            normalized = await asyncio.to_thread(normalize_post_body, raw_body, vision_client)
            async with pool.acquire() as conn:
                await persist_post_content(
                    conn,
                    post_id,
                    raw_body,
                    vision_client=vision_client,
                    embedding_client=embedding_client,
                    normalized_result=normalized,
                    structure_client=structure_client,
                    post_title=str(row["post_title"]),
                )
            if settings.orchestrator_base_url and settings.orchestrator_api_key:
                case_client = ContextualOrchestratorOperationsCaseAnalysisClient(
                    settings.orchestrator_base_url,
                    settings.orchestrator_api_key,
                )
                context = " | ".join(
                    f"{name}={row[name]}"
                    for name in (
                        "source_project_code",
                        "source_project_name",
                        "source_sales_pool_code",
                        "source_sales_pool_name",
                        "voc_type_code",
                    )
                    if row.get(name) is not None and str(row[name]).strip()
                )
                cases = await asyncio.to_thread(
                    case_client.analyze,
                    str(row["post_title"]),
                    normalized.text,
                    context,
                )
                async with pool.acquire() as conn:
                    await persist_operations_cases(
                        conn,
                        post_id,
                        raw_body,
                        metadata["lineageweave_post_session_id"],
                        cases,
                    )
            async with pool.acquire() as conn:
                complete = await post_content_is_complete(
                    conn,
                    post_id,
                    embedding_model_code=getattr(embedding_client, "resolved_model", None),
                    require_embedding=require_orchestrator_evidence,
                    require_structure=require_orchestrator_evidence,
                )
            if not complete:
                await _finish_failed_job(
                    pool,
                    post_id,
                    failure_code=_INCOMPLETE_FAILURE_CODE,
                    detail_text="post-content providers did not produce complete persisted evidence",
                    expected_attempt_count=attempt_count,
                )
                return
    except Exception as exc:  # noqa: BLE001 - durable failure is recorded for retry.
        _logger.error("post content ingestion failed for post_id=%s", post_id)
        outcome = (
            "provider_unavailable"
            if isinstance(
                exc, (HttpClientError, TimeoutError, KeyError, OSError, ValueError)
            )
            else "internal_error"
        )
        record_server_failure("post_content_ingestion", exc, outcome=outcome)
        await _finish_failed_job(
            pool,
            post_id,
            failure_code="post_content_ingestion_failed",
            detail_text=_UNEXPECTED_FAILURE_DETAIL,
            expected_attempt_count=attempt_count,
        )
        return
    await _finish_job(pool, post_id, SUCCEEDED, expected_attempt_count=attempt_count)


async def consume_post_content_stream_once(
    client: redis.Redis,
    pool: asyncpg.Pool,
    *,
    last_id: str,
    vision_factory: Callable[[], ImageContentClient],
    embedding_factory: Callable[[], EmbeddingClient],
    structure_factory: Callable[[], PostStructureClient],
) -> str:
    """Process one batch of the Valkey wake-up stream and return the new cursor.

    Reads up to 10 entries after `last_id`, runs `process_post_content_job`
    for each, and returns the last-seen entry id so the caller can resume
    from there on the next poll.
    """
    try:
        batches = await client.xread({POST_CONTENT_STREAM_KEY: last_id}, count=10, block=1000)
    except Exception:
        # Keep idle polls silent, but retain a diagnostic span for broker failures.
        with traced(
            "lineageweave.valkey.post_content_xread",
            {
                "db.system": "redis",
                "db.operation.name": "xread",
                "lineageweave.stream.kind": "post_content",
            },
        ):
            raise
    if not batches:
        return last_id
    with traced(
        "lineageweave.valkey.post_content_batch",
        {
            "db.system": "redis",
            "db.operation.name": "xread",
            "lineageweave.stream.kind": "post_content",
        },
    ):
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
        try:
            last_id = await consume_post_content_stream_once(
                client,
                pool,
                last_id=last_id,
                vision_factory=vision_factory,
                embedding_factory=embedding_factory,
                structure_factory=structure_factory,
            )
        except (redis.RedisError, OSError) as exc:
            _logger.warning(
                "post-content Valkey poll failed; retrying (error_type=%s)", type(exc).__name__
            )
            await asyncio.sleep(_BROKER_RECOVERY_DELAY_SECONDS)
