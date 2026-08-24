"""Asynchronous Global Ask job queue over the shared Valkey stream.

Why this exists: a live Ask answer is a multi-step orchestrator LLM
round-trip (retrieval, answer, lineage assembly, image evidence) that can
take minutes when the shared gateway is under load. Serving that inside
one blocking HTTP request pins a connection, times out clients, and lets
one slow provider stall every reader. This module moves the work behind
the same durable-row-plus-Valkey-stream pattern
``backend/app/post_content_queue.py`` established: the endpoint persists
a ``global_ask_job`` row and returns immediately, the in-process worker
consumes the stream, and the reader polls the job until it settles.

The durable row is the source of truth; the stream entry is only a
wake-up. A stream entry lost to a restart is recovered by periodically
republishing rows still marked ``queued``.
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any, Callable

import asyncpg
import redis.asyncio as redis

from lineageweave.http_client import HttpClientError
from lineageweave.post_chat import (
    PostChatClient,
    cited_post_evidence,
    cited_post_summaries,
)

from .lineage_ingestion import lineage_graphs_for_posts
from .post_chat_ingestion import cited_post_images, gather_global_chat_sources

GLOBAL_ASK_STREAM_KEY = "global_ask_request_stream"

QUEUED = "queued"
RUNNING = "running"
SUCCEEDED = "succeeded"
FAILED = "failed"

# Rows still `queued` after this many seconds are assumed to have lost
# their stream wake-up (process restart between insert and XADD, or a
# trimmed stream) and are republished by the worker's recovery sweep.
_REPUBLISH_AFTER_SECONDS = 60
_RECOVERY_INTERVAL_SECONDS = 30.0

_logger = logging.getLogger(__name__)


async def enqueue_global_ask_job(
    conn: asyncpg.Connection,
    client: redis.Redis,
    *,
    requesting_account_id: str,
    question_text: str,
) -> str:
    """Persist one Ask job and wake the worker; return the new job id.

    The row insert commits before the stream write so a crash between the
    two leaves a recoverable ``queued`` row rather than a stream entry
    pointing at nothing.
    """
    job_id = await conn.fetchval(
        "insert into global_ask_job (requesting_account_id, question_text)"
        " values ($1, $2) returning global_ask_job_id",
        requesting_account_id,
        question_text,
    )
    await client.xadd(GLOBAL_ASK_STREAM_KEY, {"global_ask_job_id": str(job_id)})
    return str(job_id)


async def load_account_visibility(
    conn: asyncpg.Connection, account_id: str
) -> tuple[set[str], bool]:
    """Reload an account's ABAC inputs from the database for worker-side use.

    The worker has no bearer token, so it rebuilds the two facts the
    endpoint's ``CurrentAccount`` carried: the corporate entities the
    account is affiliated with, and whether any assigned role grants
    ``post_read``. Reading them fresh at processing time means a
    revocation between submit and processing is honored.
    """
    entity_rows = await conn.fetch(
        "select corporate_entity_id from account_affiliation where user_account_id = $1",
        account_id,
    )
    has_post_read = bool(
        await conn.fetchval(
            "select exists ("
            " select 1 from account_role_assignment assignment"
            " join role_permission permission"
            "   on permission.access_role_id = assignment.access_role_id"
            " where assignment.user_account_id = $1"
            "   and permission.permission_code = 'post_read')",
            account_id,
        )
    )
    return {str(row["corporate_entity_id"]) for row in entity_rows}, has_post_read


async def compute_global_ask_answer(
    pool: asyncpg.Pool,
    *,
    question_text: str,
    corporate_entity_ids: set[str],
    chat_client: PostChatClient,
) -> dict[str, Any]:
    """Assemble one complete Ask answer payload from authorized evidence.

    This is the same retrieval → LLM answer → lineage/image assembly the
    synchronous endpoint used to perform inline; it lives here so the
    worker is its only runtime home and tests can exercise it directly.
    """

    def can_see(row: asyncpg.Record) -> bool:
        if row["visibility_code"] == "public":
            return True
        return str(row["corporate_entity_id"]) in corporate_entity_ids

    async with pool.acquire() as conn:
        sources = await gather_global_chat_sources(
            conn,
            can_see,
            corporate_entity_ids,
            question=question_text,
        )
    if not sources:
        return {
            "answer_text": "",
            "cited_post_ids": [],
            "cited_posts": [],
            "source_post_ids": [],
            "cited_post_evidence": [],
            "lineage_graph": {"nodes": [], "edges": [], "truncated": False},
            "cited_post_images": [],
            "next_action": "No authorized source posts are available for this question.",
        }
    answer = await asyncio.to_thread(chat_client.answer, question_text, sources)
    cited_ids = list(answer.cited_post_ids)
    async with pool.acquire() as conn:
        lineage_graph = await lineage_graphs_for_posts(conn, can_see, cited_ids)
        images = await cited_post_images(conn, cited_ids)
    return {
        "answer_text": answer.answer_text,
        "cited_post_ids": cited_ids,
        "cited_posts": cited_post_summaries(sources, cited_ids),
        "cited_post_evidence": cited_post_evidence(sources, cited_ids),
        "cited_post_images": images,
        "source_post_ids": [source.post_id for source in sources],
        "lineage_graph": lineage_graph,
    }


async def process_global_ask_job(
    pool: asyncpg.Pool,
    *,
    job_id: str,
    chat_factory: Callable[[], PostChatClient],
) -> None:
    """Claim, answer, and settle one Ask job.

    Claiming flips ``queued`` → ``running`` atomically so a duplicate
    stream wake-up (recovery republish racing the original entry) is a
    no-op. Every failure path settles the row as ``failed`` with a
    bounded detail string rather than leaving it stuck ``running``.
    """
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "update global_ask_job set job_status_code = $2, updated_at = now()"
            " where global_ask_job_id = $1 and job_status_code = $3"
            " returning requesting_account_id, question_text",
            job_id,
            RUNNING,
            QUEUED,
        )
    if row is None:
        return
    try:
        async with pool.acquire() as conn:
            entity_ids, has_post_read = await load_account_visibility(
                conn, str(row["requesting_account_id"])
            )
        if not has_post_read:
            raise PermissionError("account lacks the post_read permission")
        chat_client = chat_factory()
        if not chat_client.available:
            raise ConnectionError(
                "Ask Agent is unavailable: set ORCHESTRATOR_BASE_URL / ORCHESTRATOR_API_KEY"
            )
        payload = await compute_global_ask_answer(
            pool,
            question_text=str(row["question_text"]),
            corporate_entity_ids=entity_ids,
            chat_client=chat_client,
        )
    except (
        HttpClientError,
        ConnectionError,
        PermissionError,
        KeyError,
        OSError,
        ValueError,
    ) as exc:
        _logger.exception("global ask job failed for job_id=%s", job_id)
        async with pool.acquire() as conn:
            await conn.execute(
                "update global_ask_job set job_status_code = $2,"
                " failure_detail = $3, updated_at = now()"
                " where global_ask_job_id = $1",
                job_id,
                FAILED,
                str(exc)[:1000],
            )
        return
    async with pool.acquire() as conn:
        await conn.execute(
            "update global_ask_job set job_status_code = $2,"
            " answer_payload = $3::jsonb, updated_at = now()"
            " where global_ask_job_id = $1",
            job_id,
            SUCCEEDED,
            _to_json(payload),
        )


def _to_json(payload: dict[str, Any]) -> str:
    """Serialize the answer payload for the jsonb column."""
    import json

    return json.dumps(payload, ensure_ascii=False)


async def republish_queued_global_ask_jobs(
    client: redis.Redis, pool: asyncpg.Pool
) -> None:
    """Re-wake jobs whose stream entry was lost (crash/trim between steps)."""
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "select global_ask_job_id from global_ask_job"
            " where job_status_code = $1"
            "   and created_at < now() - make_interval(secs => $2)",
            QUEUED,
            _REPUBLISH_AFTER_SECONDS,
        )
    for row in rows:
        await client.xadd(
            GLOBAL_ASK_STREAM_KEY,
            {"global_ask_job_id": str(row["global_ask_job_id"])},
        )


async def consume_global_ask_stream_once(
    client: redis.Redis,
    pool: asyncpg.Pool,
    *,
    last_id: str,
    chat_factory: Callable[[], PostChatClient],
) -> str:
    """Process one batch of Ask wake-ups and return the new stream cursor."""
    batches = await client.xread({GLOBAL_ASK_STREAM_KEY: last_id}, count=10, block=1000)
    for _stream_name, entries in batches:
        for entry_id, fields in entries:
            job_id = str(fields.get("global_ask_job_id", "")).strip()
            if job_id:
                await process_global_ask_job(pool, job_id=job_id, chat_factory=chat_factory)
            last_id = str(entry_id)
    return last_id


async def _stream_tail(client: redis.Redis) -> str:
    """Start consuming after any pre-existing entries; recovery republishes them."""
    info = await client.xinfo_stream(GLOBAL_ASK_STREAM_KEY) if await client.exists(
        GLOBAL_ASK_STREAM_KEY
    ) else None
    if info and info.get("last-generated-id"):
        return str(info["last-generated-id"])
    return "0-0"


async def run_global_ask_worker(
    client: redis.Redis,
    pool: asyncpg.Pool,
    *,
    chat_factory: Callable[[], PostChatClient],
) -> None:
    """Run the at-least-once Ask consumer with periodic queued-row recovery."""
    last_id = await _stream_tail(client)
    last_recovery = 0.0
    while True:
        now = time.monotonic()
        if now - last_recovery >= _RECOVERY_INTERVAL_SECONDS:
            await republish_queued_global_ask_jobs(client, pool)
            last_recovery = now
        last_id = await consume_global_ask_stream_once(
            client,
            pool,
            last_id=last_id,
            chat_factory=chat_factory,
        )
