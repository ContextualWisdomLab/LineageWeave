"""Consume Valkey post-content wake-ups and persist derived evidence."""

from __future__ import annotations

import asyncio
import logging
import time
from collections.abc import Callable
from uuid import UUID

import asyncpg
import redis.asyncio as redis

from lineageweave.embedding_client import EmbeddingClient
from lineageweave.image_content import ImageContentClient
from lineageweave.llm_context import build_post_llm_metadata, use_llm_metadata
from lineageweave.post_content_normalization import normalize_post_body
from lineageweave.post_content_persistence import persist_post_content
from lineageweave.post_structure import PostStructureClient

from backend.app.config import load_settings
from backend.app.post_content_queue import (
    FAILED,
    POST_CONTENT_MAX_ATTEMPTS,
    POST_CONTENT_RETRY_INTERVAL,
    POST_CONTENT_STREAM_KEY,
    QUEUED,
    RUNNING,
    SUCCEEDED,
    transition_post_content_job,
    republish_queued_post_content_jobs,
)

_logger = logging.getLogger(__name__)
_RECOVERY_INTERVAL_SECONDS = 30.0
_STALE_RUNNING_INTERVAL = "15 minutes"
_INCOMPLETE_FAILURE_CODE = "post_content_ingestion_incomplete"
_ATTEMPT_LIMIT_FAILURE_CODE = "post_content_ingestion_attempt_limit"


class IncompletePostContentError(RuntimeError):
    """Indicate that a provider response did not produce complete evidence."""


async def _post_content_is_complete(
    pool: asyncpg.Pool,
    post_id: str,
    *,
    require_structure: bool,
    require_embeddings: bool,
) -> bool:
    """Check persisted evidence completeness without trusting provider optimism."""
    async with pool.acquire() as conn:
        result = await conn.fetchval(
            """
            select exists(
                       select 1
                       from post_content_unit
                       where post_id = $1
                   )
               and (
                       not $2::boolean
                       or not exists(
                           select 1
                           from post_content_unit unit
                           join post_content_unit_structure structure
                             on structure.post_content_unit_id = unit.post_content_unit_id
                           where unit.post_id = $1
                             and structure.decision_source_code = 'unresolved'
                       )
                   )
               and (
                       not $3::boolean
                       or not exists(
                           select 1
                           from post_content_unit unit
                           where unit.post_id = $1
                             and unit.unit_text <> ''
                             and not exists(
                                 select 1
                                 from post_content_embedding embedding
                                 where embedding.post_content_unit_id = unit.post_content_unit_id
                             )
                       )
                   )
            """,
            post_id,
            require_structure,
            require_embeddings,
        )
    return bool(result)


async def _claim_job(
    pool: asyncpg.Pool,
    post_id: str,
    source_body_digest: str,
) -> asyncpg.Record | None:
    async with pool.acquire() as conn:
        async with conn.transaction():
            row = await conn.fetchrow(
                f"""
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
                has_content = await conn.fetchval(
                    "select exists(select 1 from post_content_unit where post_id = $1)",
                    post_id,
                )
                if has_content:
                    return None
            if status_code == RUNNING and row["job_started_at"] is not None:
                stale = await conn.fetchval(
                    "select now() - $1 > $2::interval",
                    row["job_started_at"],
                    _STALE_RUNNING_INTERVAL,
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
    failure_code: str | None = None,
    detail_text: str | None = None,
) -> None:
    async with pool.acquire() as conn:
        async with conn.transaction():
            await transition_post_content_job(
                conn,
                post_id,
                status_code,
                failure_code=failure_code,
                detail_text=detail_text,
            )


async def _finish_failed_job(
    pool: asyncpg.Pool,
    post_id: str,
    *,
    failure_code: str,
    detail_text: str,
) -> None:
    """Schedule one retry, or persist a terminal operator-visible failure."""
    async with pool.acquire() as conn:
        async with conn.transaction():
            attempt_count = int(
                await conn.fetchval(
                    "select attempt_count from post_content_ingestion_job where post_id = $1",
                    post_id,
                )
                or 0
            )
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
    row = await _claim_job(pool, post_id, source_body_digest)
    if row is None:
        return
    try:
        raw_body = row["post_body"]
        if not isinstance(raw_body, str) or not raw_body.strip():
            raise ValueError("source post has no body")
        settings = load_settings()
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
                    embedding_model_code=settings.embedding_model or None,
                    normalized_result=normalized,
                    structure_client=structure_client,
                    post_title=str(row["post_title"]),
                )
            if not await _post_content_is_complete(
                pool,
                post_id,
                require_structure=structure_client.available,
                require_embeddings=embedding_client.available and bool(settings.embedding_model),
            ):
                raise IncompletePostContentError(
                    "post-content providers did not produce complete persisted evidence"
                )
    except Exception as exc:  # noqa: BLE001 - durable failure is recorded for retry.
        _logger.exception("post content ingestion failed for post_id=%s", post_id)
        await _finish_failed_job(
            pool,
            post_id,
            failure_code=(
                _INCOMPLETE_FAILURE_CODE
                if isinstance(exc, IncompletePostContentError)
                else "post_content_ingestion_failed"
            ),
            detail_text=str(exc)[:1000],
        )
        return
    await _finish_job(pool, post_id, SUCCEEDED)


async def consume_post_content_stream_once(
    client: redis.Redis,
    pool: asyncpg.Pool,
    *,
    last_id: str,
    vision_factory: Callable[[], ImageContentClient],
    embedding_factory: Callable[[], EmbeddingClient],
    structure_factory: Callable[[], PostStructureClient],
) -> str:
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
    last_id = "0-0"
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
