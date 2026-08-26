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
from collections.abc import Callable
from datetime import date
from typing import Any

import asyncpg
import redis.asyncio as redis
from fastapi import HTTPException, status

from lineageweave.ask_delivery import build_ask_delivery
from lineageweave.embedding_client import EmbeddingClient, NullEmbeddingClient
from lineageweave.http_client import HttpClientError
from lineageweave.observability import record_server_failure
from lineageweave.post_chat import (
    PostChatClient,
    cited_post_evidence,
    cited_post_summaries,
)
from lineageweave.public_claim_verification import (
    NullPublicClaimSearchClient,
    PublicClaimSearchClient,
    SearxngPublicClaimSearchClient,
    cited_post_ids_exclude_external,
    envelope_from_authorized_row,
    verify_public_claims,
)
from lineageweave.temporal_expressions import resolve_korean_relative_time

from .config import GLOBAL_ASK_JOB_DEADLINE_SECONDS
from .lineage_ingestion import lineage_graphs_for_posts
from .operability import log_internal_fault, log_provider_unavailable
from .post_chat_ingestion import (
    _seoul_today,
    cited_post_images,
    gather_global_chat_sources,
)

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
# Hard ceiling on one job's answer computation. Without it a hung
# orchestrator round-trip kept a job `running` indefinitely (observed:
# 17+ minutes) and, before concurrent processing, stalled every job
# behind it. Shared through config so the client-timeout validation and
# this reaper can never disagree.
JOB_DEADLINE_SECONDS = GLOBAL_ASK_JOB_DEADLINE_SECONDS
# A `running` row older than this is an orphan: a live worker's deadline
# settles every job within JOB_DEADLINE_SECONDS, so one sweep interval of
# slack past that is enough — recovering sooner shortens how long a
# crashed worker's job stays invisible to a polling reader.
_ORPHAN_RUNNING_AFTER_SECONDS = JOB_DEADLINE_SECONDS + 60
# Wake-up stream cap, mirroring the post-content stream: the durable rows
# are the source of truth, so trimming old wake-ups loses nothing.
_STREAM_MAX_LENGTH = 1000
# How many Ask jobs one worker answers at once. Answers are minutes-long
# LLM round-trips, so serial consumption would head-of-line block every
# later question behind the slowest one.
_WORKER_CONCURRENCY = 4

_logger = logging.getLogger(__name__)


class _SafeJobError(Exception):
    """Failure whose bounded message is safe to persist for the requester."""


async def enqueue_global_ask_job(
    conn: asyncpg.Connection,
    client: redis.Redis,
    *,
    requesting_account_id: str,
    question_text: str,
    corporate_entity_ids: frozenset[str],
    process_unit_ids: frozenset[str],
    verify_external: bool = False,
) -> str:
    """Persist one Ask job and wake the worker; return the new job id.

    The row insert commits before the stream write so a crash between the
    two leaves a recoverable ``queued`` row rather than a stream entry
    pointing at nothing.
    """
    async with conn.transaction():
        job_id = await conn.fetchval(
            """
            insert into global_ask_job (
                requesting_account_id, question_text, verify_external
            )
            values ($1, $2, $3) returning global_ask_job_id
            """,
            requesting_account_id,
            question_text,
            verify_external,
        )
        await conn.executemany(
            """
            insert into global_ask_job_corporate_entity_scope
                (global_ask_job_id, corporate_entity_id)
            values ($1, $2)
            """,
            [(job_id, entity_id) for entity_id in sorted(corporate_entity_ids)],
        )
        await conn.executemany(
            """
            insert into global_ask_job_process_unit_scope
                (global_ask_job_id, process_unit_id)
            values ($1, $2)
            """,
            [(job_id, process_unit_id) for process_unit_id in sorted(process_unit_ids)],
        )
    try:
        await client.xadd(
            GLOBAL_ASK_STREAM_KEY,
            {"global_ask_job_id": str(job_id)},
            maxlen=_STREAM_MAX_LENGTH,
            approximate=True,
        )
    except redis.RedisError:
        # The committed row is the source of truth; the recovery sweep
        # republishes it within a minute, so the caller still gets a
        # pollable job id instead of a 500 for a lost wake-up.
        _logger.exception("global ask wake-up publish failed for job_id=%s", job_id)
    return str(job_id)


async def load_job_visibility(
    conn: asyncpg.Connection, job_id: str, account_id: str
) -> tuple[set[str], set[str], bool, bool]:
    """Reload the queued scope, intersected with current account grants.

    The worker has no bearer token. It therefore reads the scope captured
    at enqueue time and intersects it with current affiliations, while also
    rechecking ``post_read``. A revocation can narrow a delayed job, but a
    second account affiliation can never widen it.
    """
    entity_rows = await conn.fetch(
        """
        select distinct scope.corporate_entity_id
          from global_ask_job_corporate_entity_scope scope
          join account_affiliation affiliation
            on affiliation.corporate_entity_id = scope.corporate_entity_id
           and affiliation.user_account_id = $2
         where scope.global_ask_job_id = $1
        """,
        job_id,
        account_id,
    )
    process_rows = await conn.fetch(
        """
        select distinct scope.process_unit_id
          from global_ask_job_process_unit_scope scope
          join account_affiliation affiliation
            on affiliation.process_unit_id = scope.process_unit_id
           and affiliation.user_account_id = $2
         where scope.global_ask_job_id = $1
        """,
        job_id,
        account_id,
    )
    process_scope_limited = bool(
        await conn.fetchval(
            """
            select exists (
                select 1 from global_ask_job_process_unit_scope
                 where global_ask_job_id = $1)
            """,
            job_id,
        )
    )
    has_post_read = bool(
        await conn.fetchval(
            """
            select exists (
                select 1 from account_role_assignment assignment
                join role_permission permission
                  on permission.access_role_id = assignment.access_role_id
                where assignment.user_account_id = $1
                  and permission.permission_code = 'post_read')
            """,
            account_id,
        )
    )
    return (
        {str(row["corporate_entity_id"]) for row in entity_rows},
        {str(row["process_unit_id"]) for row in process_rows},
        process_scope_limited,
        has_post_read,
    )


async def compute_global_ask_answer(
    pool: asyncpg.Pool,
    *,
    question_text: str,
    corporate_entity_ids: set[str],
    process_unit_ids: set[str],
    process_scope_limited: bool,
    chat_client: PostChatClient,
    embedding_client: EmbeddingClient | None = None,
    verify_external: bool = False,
    claim_search_client: PublicClaimSearchClient | None = None,
) -> dict[str, Any]:
    """Assemble one complete Ask answer payload from authorized evidence.

    This is the same retrieval → LLM answer → lineage/image assembly the
    synchronous endpoint used to perform inline; it lives here so the
    worker is its only runtime home and tests can exercise it directly.
    """

    def can_see(row: asyncpg.Record) -> bool:
        """Apply the requester's ABAC rule: public, or an affiliated entity's post."""
        if row["visibility_code"] == "public":
            return True
        return (
            str(row["corporate_entity_id"]) in corporate_entity_ids
            and (
                not process_scope_limited
                or str(row["process_unit_id"]) in process_unit_ids
            )
        )

    today = _seoul_today()
    try:
        async with pool.acquire() as conn:
            sources = await gather_global_chat_sources(
                conn,
                can_see,
                corporate_entity_ids,
                process_unit_ids,
                question=question_text,
                today=today,
                embedding_client=embedding_client,
            )
    except Exception as exc:
        log_internal_fault("global_ask", exc)
        record_server_failure("global_ask", exc, outcome="internal_error")
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "Ask Agent is unavailable: authorized evidence could not be assembled",
        ) from exc
    if not sources:
        delivery = build_ask_delivery("", (), ())
        payload: dict[str, Any] = {
            "answer_text": "",
            "cited_post_ids": [],
            "cited_posts": [],
            "source_post_ids": [],
            "cited_post_evidence": [],
            "lineage_graph": {"nodes": [], "edges": [], "truncated": False},
            "cited_post_images": [],
            "next_action": "No authorized source posts are available for this question.",
            "delivery": delivery,
        }
        if verify_external:
            search_client = claim_search_client or NullPublicClaimSearchClient()
            async with pool.acquire() as conn:
                envelopes = await load_authorized_public_claim_envelopes(conn, can_see)
            verification = await asyncio.to_thread(
                verify_public_claims, envelopes, search_client
            )
            cited_post_ids_exclude_external([], verification)
            payload["public_claim_verification"] = verification
        return payload
    try:
        answer = await asyncio.to_thread(
            chat_client.answer, _temporally_grounded_question(question_text, today=today), sources
        )
    except (HttpClientError, OSError) as exc:
        # Known transport/provider failure. Same generic 503 text on every
        # failure path so callers cannot probe which internal classifier
        # fired; the event_type distinction lives only in server logs.
        log_provider_unavailable("global_ask", exc)
        record_server_failure("global_ask", exc, outcome="provider_unavailable")
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "Ask Agent is unavailable: contextual-orchestrator could not complete the answer",
        ) from exc
    except (KeyError, ValueError) as exc:
        # Contract/schema fault: the orchestrator responded but its payload
        # did not match the evidence-object contract.
        log_internal_fault("global_ask", exc)
        record_server_failure("global_ask", exc, outcome="provider_unavailable")
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "Ask Agent is unavailable: contextual-orchestrator could not complete the answer",
        ) from exc
    except Exception as exc:
        # Unexpected defect. Keep the customer boundary and emit a full
        # structured internal-fault diagnostic (message-redacted).
        log_internal_fault("global_ask", exc)
        record_server_failure("global_ask", exc, outcome="internal_error")
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "Ask Agent is unavailable: contextual-orchestrator could not complete the answer",
        ) from exc
    cited_ids = list(answer.cited_post_ids)
    async with pool.acquire() as conn:
        lineage_graph = await lineage_graphs_for_posts(conn, can_see, cited_ids)
        images = await cited_post_images(conn, cited_ids)
    cited_posts = cited_post_summaries(sources, cited_ids)
    cited_evidence = cited_post_evidence(sources, cited_ids)
    payload: dict[str, Any] = {
        "answer_text": answer.answer_text,
        "cited_post_ids": cited_ids,
        "cited_posts": cited_posts,
        "cited_post_evidence": cited_evidence,
        "cited_post_images": images,
        "source_post_ids": [source.post_id for source in sources],
        "lineage_graph": lineage_graph,
        "delivery": build_ask_delivery(answer.answer_text, cited_posts, cited_evidence),
    }
    if verify_external:
        search_client = claim_search_client or NullPublicClaimSearchClient()
        async with pool.acquire() as conn:
            envelopes = await load_authorized_public_claim_envelopes(conn, can_see)
        verification = await asyncio.to_thread(
            verify_public_claims, envelopes, search_client
        )
        cited_post_ids_exclude_external(cited_ids, verification)
        payload["public_claim_verification"] = verification
        if not payload.get("next_action"):
            payload["next_action"] = verification["next_action"]
    return payload


async def load_authorized_public_claim_envelopes(
    conn: asyncpg.Connection,
    can_see: Callable[[asyncpg.Record], bool],
) -> tuple:
    """Re-read egress-eligible public envelopes through the current ABAC gate.

    A missing table is unavailable, not an invented claim. Private or
    ineligible rows never reach SearXNG.
    """
    try:
        rows = await conn.fetch(
            """
            select envelope.public_claim_envelope_id,
                   envelope.source_post_id,
                   post.post_title as source_post_title,
                   envelope.claim_kind_code,
                   envelope.subject_label,
                   envelope.claim_text,
                   envelope.truth_status_code,
                   envelope.event_occurred_at,
                   envelope.egress_eligible,
                   post.visibility_code,
                   post.corporate_entity_id,
                   post.process_unit_id
              from public_claim_envelope envelope
              join source_post post
                on post.post_id = envelope.source_post_id
             where envelope.egress_eligible
               and post.visibility_code = 'public'
             order by envelope.created_at, envelope.public_claim_envelope_id
            """
        )
    except asyncpg.UndefinedTableError:
        return ()
    envelopes = []
    for row in rows:
        if not can_see(row):
            continue
        envelope = envelope_from_authorized_row(row)
        if envelope is not None:
            envelopes.append(envelope)
    return tuple(envelopes)


def _public_claim_search_client() -> PublicClaimSearchClient:
    """Live SearXNG client when configured; otherwise unavailable."""
    from backend.app.config import load_settings

    settings = load_settings()
    if not settings.searxng_base_url:
        return NullPublicClaimSearchClient()
    try:
        return SearxngPublicClaimSearchClient(settings.searxng_base_url)
    except ValueError:
        return NullPublicClaimSearchClient()


def _temporally_grounded_question(question_text: str, *, today: date | None = None) -> str:
    """Restate a resolved relative-time window inside the question.

    Retrieval already scopes sources to the resolved window, but the
    prompt's numbered sources carry no dates — so without this clause the
    model answers a question like "7개월 전에 무슨 일이 있었나요?" with
    "no date information" and cites nothing (observed live). Naming the
    resolved window, and that every source falls inside it, lets the
    model answer from the evidence it was given.
    """
    today = today or _seoul_today()
    window = resolve_korean_relative_time(question_text, today=today)
    if window is None:
        return question_text
    start_date, end_date = window
    # Phrasing matters: an earlier clause that only named the window was
    # read by the model as the reference point ("now"), which re-subtracted
    # the offset and looked for events seven further months back. Anchor
    # today's date and equate the expression to the window outright.
    return (
        f"{question_text}\n(오늘은 {today.isoformat()}입니다. 질문의 상대 시점 표현은 "
        f"{start_date.isoformat()}부터 {end_date.isoformat()}까지의 기간을 가리킵니다. "
        "제공된 소스 게시물은 모두 이 기간에 작성된 것이므로, 이 기간의 일을 "
        "이 소스들로 답하십시오.)"
    )


async def process_global_ask_job(
    pool: asyncpg.Pool,
    *,
    job_id: str,
    chat_factory: Callable[[], PostChatClient],
    embedding_factory: Callable[[], EmbeddingClient] = NullEmbeddingClient,
) -> None:
    """Claim, answer, and settle one Ask job.

    Claiming flips ``queued`` → ``running`` atomically so a duplicate
    stream wake-up (recovery republish racing the original entry) is a
    no-op. Every failure path settles the row as ``failed`` with a
    bounded detail string rather than leaving it stuck ``running``.
    """
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            update global_ask_job set job_status_code = $2, updated_at = now()
            where global_ask_job_id = $1 and job_status_code = $3
            returning requesting_account_id, question_text, verify_external
            """,
            job_id,
            RUNNING,
            QUEUED,
        )
    if row is None:
        return
    try:
        async with pool.acquire() as conn:
            (
                entity_ids,
                process_unit_ids,
                process_scope_limited,
                has_post_read,
            ) = await load_job_visibility(
                conn, job_id, str(row["requesting_account_id"])
            )
        if not has_post_read:
            raise _SafeJobError("account lacks the post_read permission")
        chat_client = chat_factory()
        if not chat_client.available:
            raise _SafeJobError(
                "Ask Agent is unavailable: set ORCHESTRATOR_BASE_URL / ORCHESTRATOR_API_KEY"
            )
        payload = await asyncio.wait_for(
            compute_global_ask_answer(
                pool,
                question_text=str(row["question_text"]),
                corporate_entity_ids=entity_ids,
                process_unit_ids=process_unit_ids,
                process_scope_limited=process_scope_limited,
                chat_client=chat_client,
                embedding_client=embedding_factory(),
                verify_external=bool(row.get("verify_external", False)),
                claim_search_client=_public_claim_search_client(),
            ),
            timeout=JOB_DEADLINE_SECONDS,
        )
    except asyncio.CancelledError:
        # Shutdown: leave the row `running`; the recovery sweep re-queues
        # it after the orphan window on the next process start.
        raise
    except Exception as exc:
        # A narrow exception tuple here once let an unexpected error kill
        # the task silently and strand the row `running` until orphan
        # recovery (observed live) — every failure settles the job.
        # Full exception is logged internally for operators; the reader
        # only ever sees a generic, bounded message, never the raw
        # exception text (issue #361 -- a leaked orchestrator/provider
        # exception once exposed internals straight to a client).
        _logger.exception("global ask job failed for job_id=%s", job_id)
        if isinstance(exc, _SafeJobError):
            # Raised locally with a pre-authored, safe message (permission
            # state / missing config) — never a provider-boundary leak.
            detail = str(exc)
        elif isinstance(exc, asyncio.TimeoutError):
            detail = f"job exceeded the {JOB_DEADLINE_SECONDS}s deadline"
        else:
            # Provider responses/exceptions can carry credentials, gateway
            # diagnostics, or model output (ADR 0123): never persist the
            # raw exception text as a durable `failure_detail`. The
            # traceback just logged keeps it for operator debugging only.
            detail = (
                "Ask Agent is unavailable: contextual-orchestrator returned "
                "no complete evidence object"
            )
        async with pool.acquire() as conn:
            await conn.execute(
                """
                update global_ask_job set job_status_code = $2,
                    failure_detail = $3, updated_at = now()
                where global_ask_job_id = $1
                """,
                job_id,
                FAILED,
                detail[:1000],
            )
        return
    async with pool.acquire() as conn:
        await conn.execute(
            """
            update global_ask_job set job_status_code = $2,
                answer_payload = $3::jsonb, updated_at = now()
            where global_ask_job_id = $1
            """,
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
    """Re-wake lost jobs: stale ``queued`` rows and orphaned ``running`` rows.

    A ``queued`` row older than the republish window lost its stream
    entry (crash or trim between insert and XADD). A ``running`` row
    older than the orphan window belongs to a worker that died mid-job —
    the per-job deadline guarantees a live worker settles sooner — so it
    is flipped back to ``queued`` and re-woken for at-least-once
    delivery.
    """
    async with pool.acquire() as conn:
        # Fully parameterized ($1..$3 with module constants); the rule
        # misreads the literal-plus-arguments shape, same as the existing
        # suppressions in report_ingestion.py.
        await conn.execute(  # nosemgrep: python.lang.security.audit.sqli.asyncpg-sqli.asyncpg-sqli
            """
            update global_ask_job set job_status_code = $1, updated_at = now()
            where job_status_code = $2
              and updated_at < now() - interval '1 second' * $3
            """,
            QUEUED,
            RUNNING,
            _ORPHAN_RUNNING_AFTER_SECONDS,
        )
        rows = await conn.fetch(  # nosemgrep: python.lang.security.audit.sqli.asyncpg-sqli.asyncpg-sqli
            """
            select global_ask_job_id from global_ask_job
            where job_status_code = $1
              and created_at < now() - interval '1 second' * $2
            """,
            QUEUED,
            _REPUBLISH_AFTER_SECONDS,
        )
    for row in rows:
        await client.xadd(
            GLOBAL_ASK_STREAM_KEY,
            {"global_ask_job_id": str(row["global_ask_job_id"])},
            maxlen=_STREAM_MAX_LENGTH,
            approximate=True,
        )


async def consume_global_ask_stream_once(
    client: redis.Redis,
    pool: asyncpg.Pool,
    *,
    last_id: str,
    chat_factory: Callable[[], PostChatClient],
    embedding_factory: Callable[[], EmbeddingClient] = NullEmbeddingClient,
    limiter: asyncio.Semaphore | None = None,
    tasks: set[asyncio.Task] | None = None,
) -> str:
    """Dispatch one batch of Ask wake-ups and return the new stream cursor.

    Jobs launch as bounded concurrent tasks rather than being awaited
    inline: an answer is a minutes-long LLM round-trip, and serial
    consumption head-of-line blocked every question behind the slowest
    one (observed live). The queued->running claim inside
    ``process_global_ask_job`` keeps duplicate wake-ups no-ops, so
    concurrent dispatch preserves at-least-once semantics. Without a
    ``limiter`` (direct test calls), jobs are processed inline.
    """
    batches = await client.xread({GLOBAL_ASK_STREAM_KEY: last_id}, count=10, block=1000)
    for _stream_name, entries in batches:
        for entry_id, fields in entries:
            job_id = str(fields.get("global_ask_job_id", "")).strip()
            if job_id:
                if limiter is None:
                    await process_global_ask_job(
                        pool,
                        job_id=job_id,
                        chat_factory=chat_factory,
                        embedding_factory=embedding_factory,
                    )
                else:
                    await limiter.acquire()
                    task = asyncio.create_task(
                        _process_and_release(
                            pool,
                            job_id=job_id,
                            chat_factory=chat_factory,
                            embedding_factory=embedding_factory,
                            limiter=limiter,
                        )
                    )
                    if tasks is not None:
                        tasks.add(task)
                        task.add_done_callback(tasks.discard)
            last_id = str(entry_id)
    return last_id


async def _process_and_release(
    pool: asyncpg.Pool,
    *,
    job_id: str,
    chat_factory: Callable[[], PostChatClient],
    embedding_factory: Callable[[], EmbeddingClient],
    limiter: asyncio.Semaphore,
) -> None:
    """Run one dispatched job and free its concurrency slot afterwards."""
    try:
        await process_global_ask_job(
            pool,
            job_id=job_id,
            chat_factory=chat_factory,
            embedding_factory=embedding_factory,
        )
    finally:
        limiter.release()


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
    embedding_factory: Callable[[], EmbeddingClient] = NullEmbeddingClient,
) -> None:
    """Run the at-least-once Ask consumer with periodic queued-row recovery."""
    last_id = await _stream_tail(client)
    last_recovery = 0.0
    limiter = asyncio.Semaphore(_WORKER_CONCURRENCY)
    tasks: set[asyncio.Task] = set()
    try:
        while True:
            try:
                now = time.monotonic()
                if now - last_recovery >= _RECOVERY_INTERVAL_SECONDS:
                    await republish_queued_global_ask_jobs(client, pool)
                    last_recovery = now
                last_id = await consume_global_ask_stream_once(
                    client,
                    pool,
                    last_id=last_id,
                    chat_factory=chat_factory,
                    embedding_factory=embedding_factory,
                    limiter=limiter,
                    tasks=tasks,
                )
            except asyncio.CancelledError:
                raise
            except Exception:
                _logger.exception("global ask worker round failed; retrying")
                await asyncio.sleep(5)
    finally:
        # Shutdown: cancel in-flight jobs; recovery re-queues their
        # orphaned `running` rows on the next process start.
        for task in tasks:
            task.cancel()
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
