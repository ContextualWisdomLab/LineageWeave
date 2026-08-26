"""Consume Valkey post-content wake-ups and persist derived evidence."""

from __future__ import annotations

import asyncio
import logging
import time
from collections.abc import Awaitable, Callable
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
    ensure_post_content_job,
    post_content_is_complete,
    republish_queued_post_content_jobs,
    transition_post_content_job,
)
from backend.app.operations_case_ingestion import persist_operations_cases
from backend.app.post_chat_ingestion import (
    find_project_sibling_post_ids,
    gather_chat_sources,
)
from lineageweave.embedding_client import EmbeddingClient, NullEmbeddingClient
from lineageweave.http_client import HttpClientError
from lineageweave.image_content import ImageContentClient
from lineageweave.llm_context import build_post_llm_metadata, use_llm_metadata
from lineageweave.observability import record_server_failure, traced
from lineageweave.operations_case_analysis import (
    ContextualOrchestratorOperationsCaseAnalysisClient,
    OperationsEvidenceSource,
)
from lineageweave.post_content_normalization import normalize_post_body
from lineageweave.post_content_persistence import persist_post_content
from lineageweave.post_structure import PostStructureClient

_logger = logging.getLogger(__name__)
_RECOVERY_INTERVAL_SECONDS = 30.0
_BROKER_RECOVERY_DELAY_SECONDS = 1.0
_INCOMPLETE_FAILURE_CODE = "post_content_ingestion_incomplete"
_ATTEMPT_LIMIT_FAILURE_CODE = "post_content_ingestion_attempt_limit"
_SOURCE_BODY_MISSING_FAILURE_CODE = "post_content_source_body_missing"
_UNEXPECTED_FAILURE_DETAIL = (
    "post-content provider operation failed; retry the ingestion job"
)


async def _operations_evidence_sources(
    pool: asyncpg.Pool,
    post_id: str,
    focal_row: asyncpg.Record,
    vision_client: ImageContentClient,
) -> tuple[OperationsEvidenceSource, ...]:
    """Reuse authorized lineage/semantic chat retrieval for case inference."""
    focal_entity = str(focal_row["corporate_entity_id"])
    focal_process = focal_row.get("process_unit_id")

    def can_see(row: asyncpg.Record) -> bool:
        """Keep linked private evidence inside the focal entity and PU scope."""
        return row["visibility_code"] == "public" or (
            str(row["corporate_entity_id"]) == focal_entity
            and row.get("process_unit_id") == focal_process
        )

    async with pool.acquire() as conn:
        sources = await gather_chat_sources(conn, post_id, can_see, vision_client)
        if not sources:
            return ()
        source_post_ids = [UUID(source.post_id) for source in sources]
        source_times = {
            str(row["post_id"]): (
                row["observed_at"],
                "event_occurred_at"
                if row["event_occurred_at"] is not None
                else "created_at",
            )
            for row in await conn.fetch(
                "select post_id, event_occurred_at, "
                "coalesce(event_occurred_at, created_at) as observed_at "
                "from source_post where post_id = any($1::uuid[])",
                source_post_ids,
            )
        }
    if any(source.post_id not in source_times for source in sources):
        raise RuntimeError("authorized evidence source clock unavailable")
    return tuple(
        OperationsEvidenceSource(
            source.post_id,
            source.post_title,
            source.post_body
            + (
                "\nPersisted semantic evidence:\n" + "\n".join(source.evidence_facts)
                if source.evidence_facts
                else ""
            ),
            source_times[source.post_id][0],
            source_times[source.post_id][1],
        )
        for source in sources
    )


async def _persist_operations_case_analysis_if_needed(
    pool: asyncpg.Pool,
    post_id: str,
    source_body_digest: str,
    raw_body: str,
    row: asyncpg.Record,
    vision_client: ImageContentClient,
    session_id: str,
    orchestrator_base_url: str,
    orchestrator_api_key: str,
) -> None:
    """Persist evidence-bound cases once per exact source-body version."""
    async with pool.acquire() as conn:
        already_persisted = bool(
            await conn.fetchval(
                "select exists (select 1 from operations_case_analysis "
                "where post_id = $1 and source_body_sha256 = $2)",
                post_id,
                source_body_digest,
            )
        )
    if already_persisted:
        return
    case_client = ContextualOrchestratorOperationsCaseAnalysisClient(
        orchestrator_base_url,
        orchestrator_api_key,
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
    evidence_sources = await _operations_evidence_sources(
        pool, post_id, row, vision_client
    )
    cases = await asyncio.to_thread(case_client.analyze, evidence_sources, context)
    async with pool.acquire() as conn:
        await persist_operations_cases(
            conn,
            post_id,
            raw_body,
            session_id,
            cases,
        )


async def _requeue_project_missing_case_jobs(
    pool: asyncpg.Pool,
    post_id: str,
) -> int:
    """Re-analyze older project siblings that still lack required facts."""
    async with pool.acquire() as conn:
        async with conn.transaction():
            sibling_ids = await find_project_sibling_post_ids(conn, post_id)
            if not sibling_ids:
                return 0
            rows = await conn.fetch(
                """
                select distinct post.post_id, post.post_body
                  from operations_case_missing_fact missing
                  join source_post post on post.post_id = missing.post_id
                 join post_content_ingestion_job job on job.post_id = missing.post_id
                 where missing.post_id = any($1::uuid[])
                   and job.status_code = $2
                   and nullif(btrim(post.post_body), '') is not null
                 order by post.post_id
                """,
                [UUID(sibling_id) for sibling_id in sibling_ids],
                SUCCEEDED,
            )
            queued = 0
            for row in rows:
                request = await ensure_post_content_job(
                    conn,
                    str(row["post_id"]),
                    str(row["post_body"]),
                    content_complete=False,
                )
                queued += int(request.should_publish)
            return queued


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
                       j.queued_at as job_queued_at,
                       (
                           select analysis.source_body_sha256
                             from operations_case_analysis analysis
                            where analysis.post_id = p.post_id
                       ) as case_analysis_source_body_sha256
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
                    "select now() - $1::timestamptz > $2::interval",
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
    defer_embedding: bool = False,
) -> tuple[int, asyncio.Task[None] | None] | None:
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
    operations_task: asyncio.Task[None] | None = None
    try:
        metadata = build_post_llm_metadata(post_id, row)
        embedding_client = NullEmbeddingClient() if defer_embedding else embedding_factory()
        structure_client = structure_factory()
        with use_llm_metadata(metadata):
            vision_client = vision_factory()
            if settings.orchestrator_base_url and settings.orchestrator_api_key:
                operations_task = asyncio.create_task(
                    _persist_operations_case_analysis_if_needed(
                        pool,
                        post_id,
                        source_body_digest,
                        raw_body,
                        row,
                        vision_client,
                        metadata["lineageweave_post_session_id"],
                        settings.orchestrator_base_url,
                        settings.orchestrator_api_key,
                    )
                )
            normalized = await asyncio.to_thread(
                normalize_post_body, raw_body, vision_client
            )
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
            async with pool.acquire() as conn:
                complete = await post_content_is_complete(
                    conn,
                    post_id,
                    embedding_model_code=getattr(
                        embedding_client, "resolved_model", None
                    ),
                    require_embedding=require_orchestrator_evidence,
                    require_structure=require_orchestrator_evidence,
                )
            if defer_embedding:
                return attempt_count, operations_task
            if operations_task is not None:
                await operations_task
            if not complete:
                await _finish_failed_job(
                    pool,
                    post_id,
                    failure_code=_INCOMPLETE_FAILURE_CODE,
                    detail_text="post-content providers did not produce complete persisted evidence",
                    expected_attempt_count=attempt_count,
                )
                return
            if (
                settings.orchestrator_base_url
                and settings.orchestrator_api_key
                and row.get("case_analysis_source_body_sha256")
                != source_body_digest
            ):
                try:
                    await _requeue_project_missing_case_jobs(pool, post_id)
                except Exception as exc:  # noqa: BLE001 - primary evidence is complete.
                    _logger.error("project sibling requeue failed for post_id=%s", post_id)
                    record_server_failure(
                        "post_content_sibling_requeue",
                        exc,
                        outcome="provider_unavailable",
                    )
    except Exception as exc:  # noqa: BLE001 - durable failure is recorded for retry.
        if operations_task is not None:
            try:
                await operations_task
            except Exception:  # noqa: BLE001 - the content failure remains the durable retry cause.
                pass
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
    return attempt_count, None


async def _persist_bulk_embeddings(
    pool: asyncpg.Pool, post_ids: list[str], embedding_client: EmbeddingClient
) -> None:
    """Embed all missing semantic units in one provenance-aligned bulk request."""
    if not post_ids or not embedding_client.available:
        return
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            select 'unit' as target_kind, unit.post_content_unit_id as target_id,
                   unit.unit_text as input_text, post.post_id,
                   post.author_account_id, post.corporate_entity_id, post.process_unit_id
              from post_content_unit unit
              join source_post post on post.post_id = unit.post_id
              left join post_content_embedding embedding using (post_content_unit_id)
             where unit.post_id = any($1::uuid[])
               and nullif(btrim(unit.unit_text), '') is not null
               and embedding.post_content_embedding_id is null
            union all
            select 'region', region.post_content_image_region_id,
                   concat_ws(' ', region.caption, region.extracted_text), post.post_id,
                   post.author_account_id, post.corporate_entity_id, post.process_unit_id
              from post_content_image_region region
              join post_content_image image using (post_content_image_id)
              join post_content_unit unit using (post_content_unit_id)
              join source_post post on post.post_id = unit.post_id
              left join post_content_image_region_embedding embedding
                using (post_content_image_region_id)
             where unit.post_id = any($1::uuid[])
               and region.description_status_code = 'described'
               and nullif(btrim(concat_ws(' ', region.caption, region.extracted_text)), '') is not null
               and embedding.post_content_image_region_embedding_id is null
             order by post_id, target_kind, target_id
            """,
            [UUID(post_id) for post_id in post_ids],
        )
    if not rows:
        return
    embed_many = getattr(embedding_client, "embed_many", None)
    if not callable(embed_many):
        raise RuntimeError("bulk embedding client is unavailable")
    vectors = await asyncio.to_thread(
        embed_many,
        [str(row["input_text"]) for row in rows],
        input_metadata=[
            {
                "session_id": f"post:{row['post_id']}",
                "post_id": str(row["post_id"]),
                "target_kind": str(row["target_kind"]),
                "target_id": str(row["target_id"]),
            }
            for row in rows
        ],
        input_attributions=[
            {
                key: str(value)
                for key, value in {
                    "account": row["author_account_id"],
                    "team": row["process_unit_id"],
                    "company": row["corporate_entity_id"],
                }.items()
                if value is not None
            }
            for row in rows
        ],
    )
    model = getattr(embedding_client, "resolved_model", None)
    if not isinstance(model, str) or not model:
        raise ValueError("bulk embedding response did not identify its model")
    unit_dimensions: list[tuple[object, int, float]] = []
    region_dimensions: list[tuple[object, int, float]] = []
    async with pool.acquire() as conn, conn.transaction():
        for row, vector in zip(rows, vectors, strict=True):
            is_unit = row["target_kind"] == "unit"
            embedding_id = await conn.fetchval(
                (
                    "insert into post_content_embedding (post_content_unit_id, embedding_model_code, embedding_dimension_count) values ($1, $2, $3) returning post_content_embedding_id"
                    if is_unit
                    else "insert into post_content_image_region_embedding (post_content_image_region_id, embedding_model_code, embedding_dimension_count) values ($1, $2, $3) returning post_content_image_region_embedding_id"
                ),
                row["target_id"],
                model,
                len(vector),
            )
            target = unit_dimensions if is_unit else region_dimensions
            target.extend(
                (embedding_id, index, float(value))
                for index, value in enumerate(vector)
            )
        if unit_dimensions:
            await conn.executemany(
                "insert into post_content_embedding_value (post_content_embedding_id, dimension_index, dimension_value) values ($1, $2, $3)",
                unit_dimensions,
            )
        if region_dimensions:
            await conn.executemany(
                "insert into post_content_image_region_embedding_value (post_content_image_region_embedding_id, dimension_index, dimension_value) values ($1, $2, $3)",
                region_dimensions,
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
    """Process one batch of the Valkey wake-up stream and return the new cursor.

    Reads up to 10 entries after `last_id`, runs `process_post_content_job`
    for each, and returns the last-seen entry id so the caller can resume
    from there on the next poll.
    """
    try:
        batches = await client.xread(
            {POST_CONTENT_STREAM_KEY: last_id}, count=10, block=1000
        )
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
        embedding_client = embedding_factory()
        bulk_enabled = embedding_client.available
        deferred: list[tuple[str, int, asyncio.Task[None] | None]] = []
        pending: list[
            tuple[str, Awaitable[tuple[int, asyncio.Task[None] | None] | None]]
        ] = []
        for _stream_name, entries in batches:
            for entry_id, fields in entries:
                post_id = str(fields.get("post_id", "")).strip()
                digest = str(fields.get("source_body_sha256", "")).strip()
                try:
                    UUID(post_id)
                except ValueError:
                    post_id = ""
                if post_id and len(digest) == 64:
                    pending.append(
                        (
                            post_id,
                            process_post_content_job(
                                pool,
                                post_id=post_id,
                                source_body_digest=digest,
                                vision_factory=vision_factory,
                                embedding_factory=embedding_factory,
                                structure_factory=structure_factory,
                                defer_embedding=bulk_enabled,
                            ),
                        )
                    )
                last_id = str(entry_id)
        if pending:
            attempt_counts = await asyncio.gather(*(job for _post_id, job in pending))
            deferred.extend(
                (post_id, result[0], result[1])
                for (post_id, _job), result in zip(pending, attempt_counts, strict=True)
                if result is not None
            )
        if deferred:
            operations_tasks = [task for _post_id, _attempt, task in deferred if task is not None]
            results = await asyncio.gather(
                _persist_bulk_embeddings(
                    pool, [post_id for post_id, _attempt, _task in deferred], embedding_client
                ),
                *operations_tasks,
                return_exceptions=True,
            )
            bulk_error = results[0] if isinstance(results[0], Exception) else None
            if bulk_error is not None:
                record_server_failure(
                    "post_content_bulk_embedding", bulk_error, outcome="provider_unavailable"
                )
                for post_id, attempt_count, _task in deferred:
                    await _finish_failed_job(
                        pool,
                        post_id,
                        failure_code=_INCOMPLETE_FAILURE_CODE,
                        detail_text="bulk embedding did not produce complete persisted evidence",
                        expected_attempt_count=attempt_count,
                    )
            else:
                for post_id, attempt_count, operations_task in deferred:
                    if operations_task is not None and operations_task.exception() is not None:
                        await _finish_failed_job(
                            pool,
                            post_id,
                            failure_code="operations_case_analysis_failed",
                            detail_text="operations analysis did not produce persisted evidence",
                            expected_attempt_count=attempt_count,
                        )
                        continue
                    async with pool.acquire() as conn:
                        complete = await post_content_is_complete(
                            conn,
                            post_id,
                            embedding_model_code=getattr(embedding_client, "resolved_model", None),
                            require_embedding=True,
                            require_structure=True,
                        )
                    if complete:
                        await _finish_job(
                            pool, post_id, SUCCEEDED, expected_attempt_count=attempt_count
                        )
                        try:
                            await _requeue_project_missing_case_jobs(pool, post_id)
                        except Exception as exc:  # noqa: BLE001 - primary evidence is complete.
                            record_server_failure(
                                "post_content_sibling_requeue", exc, outcome="provider_unavailable"
                            )
                    else:
                        await _finish_failed_job(
                            pool,
                            post_id,
                            failure_code=_INCOMPLETE_FAILURE_CODE,
                            detail_text="bulk embedding did not produce complete persisted evidence",
                            expected_attempt_count=attempt_count,
                        )
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
                "post-content Valkey poll failed; retrying (error_type=%s)",
                type(exc).__name__,
            )
            await asyncio.sleep(_BROKER_RECOVERY_DELAY_SECONDS)
