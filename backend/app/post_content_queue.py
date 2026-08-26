"""Durable post-content ingestion jobs with a Valkey wake-up stream."""

from __future__ import annotations

import hashlib
from datetime import timedelta
from dataclasses import dataclass
from typing import Any

import asyncpg
import redis.asyncio as redis

from backend.app.post_eligibility import SOURCE_POST_ELIGIBILITY_SQL
from lineageweave.observability import traced

POST_CONTENT_STREAM_KEY = "post-content-ingestion"
QUEUED = "post_content_ingestion_queued"
RUNNING = "post_content_ingestion_running"
SUCCEEDED = "post_content_ingestion_succeeded"
FAILED = "post_content_ingestion_failed"
STALE_RUNNING_INTERVAL = timedelta(minutes=15)
_ACTIVE = {QUEUED, RUNNING}
POST_CONTENT_MAX_ATTEMPTS = 3
POST_CONTENT_RETRY_INTERVAL = timedelta(minutes=5)


@dataclass(frozen=True)
class PostContentJobRequest:
    """One queued or running post-content ingestion job."""

    post_id: str
    source_body_sha256: str
    status_code: str
    should_publish: bool


def source_body_sha256(body: str) -> str:
    """Hash the immutable source representation, never the derived content."""
    return hashlib.sha256(body.encode("utf-8")).hexdigest()


def post_content_api_status(status_code: str | None, *, content_present: bool) -> str:
    """Map a job's internal status code to the API-facing status string."""
    if status_code in _ACTIVE:
        return "processing"
    if status_code == FAILED:
        return "unavailable"
    if content_present:
        return "ready"
    return "unavailable"


async def post_content_is_complete(
    conn: asyncpg.Connection,
    post_id: str,
    *,
    embedding_model_code: str | None = None,
    require_embedding: bool = False,
    require_structure: bool = False,
) -> bool:
    """Require configured semantic, structure, and region evidence before ready."""
    return bool(
        await conn.fetchval(
            """
            select exists(
                       select 1
                         from post_content_unit unit
                        where unit.post_id = $1
                   )
               and (
                   not $3::boolean
                       or (
                           not exists(
                               select 1
                                 from post_content_unit unit
                                 left join post_content_embedding embedding
                                   on embedding.post_content_unit_id = unit.post_content_unit_id
                                  and ($2::text is null or embedding.embedding_model_code = $2)
                                where unit.post_id = $1
                                  and embedding.post_content_embedding_id is null
                           )
                           and not exists(
                               select 1
                                 from post_content_unit unit
                                 join post_content_image image
                                   on image.post_content_unit_id = unit.post_content_unit_id
                                 join post_content_image_region region
                                   on region.post_content_image_id = image.post_content_image_id
                                 left join post_content_image_region_embedding embedding
                                   on embedding.post_content_image_region_id = region.post_content_image_region_id
                                  and ($2::text is null or embedding.embedding_model_code = $2)
                                where unit.post_id = $1
                                  and region.description_status_code = 'described'
                                  and embedding.post_content_image_region_embedding_id is null
                           )
                       )
                   )
               and (
                       not $4::boolean
                       or not exists(
                           select 1
                             from post_content_unit unit
                             left join post_content_unit_structure structure
                               on structure.post_content_unit_id = unit.post_content_unit_id
                            where unit.post_id = $1
                              and unit.unit_kind_code <> 'image'
                              and (
                                  structure.post_content_unit_structure_id is null
                                  or structure.decision_source_code = 'unresolved'
                              )
                       )
                   )
            """,
            post_id,
            embedding_model_code,
            require_embedding,
            require_structure,
        )
    )


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
        with traced(
            "lineageweave.valkey.post_content_xadd",
            {"db.system": "redis", "db.operation.name": "xadd", "lineageweave.stream.kind": "post_content"},
        ):
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
    expected_attempt_count: int | None = None,
    channel_stage_code: str | None = None,
    http_status: int | None = None,
    orchestrator_error_code: str | None = None,
    retryable: bool | None = None,
    session_correlation_id: str | None = None,
    failure_error_type: str | None = None,
    failure_validation_code: str | None = None,
    failure_validation_path: str | None = None,
) -> bool:
    """Update one job attempt and append its lifecycle event atomically.

    ``expected_attempt_count`` fences stale workers after lease recovery.  A
    late completion from an older attempt must not overwrite the newer
    attempt's status or append a misleading lifecycle event.
    """
    updated = await conn.execute(
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
            next_attempt_at = null,
            updated_at = now(),
            last_error_code = $7,
            last_error_detail = $8,
            failure_channel_stage_code = $10,
            failure_http_status = $11,
            failure_orchestrator_error_code = $12,
            failure_retryable = $13,
            failure_session_correlation_id = $14,
            failure_error_type = $15,
            failure_validation_code = $16,
            failure_validation_path = $17
        where post_id = $1
          and ($9::integer is null or attempt_count = $9)
        """,
        post_id,
        status_code,
        RUNNING,
        SUCCEEDED,
        FAILED,
        QUEUED,
        failure_code,
        detail_text,
        expected_attempt_count,
        channel_stage_code,
        http_status,
        orchestrator_error_code,
        retryable,
        session_correlation_id,
        failure_error_type,
        failure_validation_code,
        failure_validation_path,
    )
    if not updated.endswith(" 1"):
        return False
    await _record_status(
        conn,
        post_id,
        status_code,
        failure_code=failure_code,
        detail_text=detail_text,
    )
    return True


async def defer_post_content_job(
    conn: asyncpg.Connection,
    post_id: str,
    *,
    expected_attempt_count: int,
    retry_after_seconds: int,
) -> bool:
    """Return one unadmitted lease to queued without consuming an attempt."""
    if type(retry_after_seconds) is not int or retry_after_seconds <= 0:
        raise ValueError("retry_after_seconds must be a positive integer")
    updated = await conn.execute(
        """
        update post_content_ingestion_job
        set status_code = $2,
            attempt_count = attempt_count - 1,
            queued_at = now(),
            next_attempt_at = now() + make_interval(secs => $5),
            started_at = null,
            completed_at = null,
            updated_at = now(),
            last_error_code = $6,
            last_error_detail = $7
        where post_id = $1
          and status_code = $3
          and attempt_count = $4
          and attempt_count > 0
        """,
        post_id,
        QUEUED,
        RUNNING,
        expected_attempt_count,
        retry_after_seconds,
        "no_viable_agent",
        "Analysis capacity is being restored; this record will retry automatically.",
    )
    if not updated.endswith(" 1"):
        return False
    await _record_status(
        conn,
        post_id,
        QUEUED,
        failure_code="no_viable_agent",
        detail_text="Analysis capacity is being restored; this record will retry automatically.",
    )
    return True


async def ensure_post_content_job(
    conn: asyncpg.Connection,
    post_id: str,
    body: str,
    *,
    content_complete: bool,
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
        initial_status = SUCCEEDED if content_complete else QUEUED
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
        or (status_code == SUCCEEDED and not content_complete)
    )
    if needs_requeue:
        await conn.execute(
            """
            update post_content_ingestion_job
            set source_body_sha256 = $2,
                status_code = $3,
                attempt_count = 0,
                queued_at = now(),
                next_attempt_at = null,
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


async def enqueue_post_content_backfill(
    pool: asyncpg.Pool,
    client: redis.Redis | None,
    *,
    limit: int,
    require_embedding: bool,
    require_structure: bool,
) -> dict[str, int]:
    """Durably enqueue one bounded page of eligible incomplete source posts.

    PostgreSQL is committed before Valkey is touched.  A missing wake-up is
    therefore recoverable by :func:`republish_queued_post_content_jobs` rather
    than turning an operator request into lost work.  Active and terminal jobs
    are excluded so repeated requests neither duplicate work nor reset the
    explicit retry boundary.
    """
    if not 1 <= limit <= 200:
        raise ValueError("limit must be between 1 and 200")
    query = f"""
        select post.post_id, post.post_body
          from source_post post
          left join post_content_ingestion_job job on job.post_id = post.post_id
         where {SOURCE_POST_ELIGIBILITY_SQL.format(alias='post')}
           and (job.post_id is null or job.status_code = $1)
           and (
               not exists (
                   select 1 from post_content_unit unit
                    where unit.post_id = post.post_id
               )
               or ($2::boolean and exists (
                   select 1
                     from post_content_unit unit
                     left join post_content_embedding embedding
                       on embedding.post_content_unit_id = unit.post_content_unit_id
                    where unit.post_id = post.post_id
                      and embedding.post_content_embedding_id is null
               ))
               or ($2::boolean and exists (
                   select 1
                     from post_content_unit unit
                     join post_content_image image
                       on image.post_content_unit_id = unit.post_content_unit_id
                     join post_content_image_region region
                       on region.post_content_image_id = image.post_content_image_id
                     left join post_content_image_region_embedding embedding
                       on embedding.post_content_image_region_id = region.post_content_image_region_id
                    where unit.post_id = post.post_id
                      and region.description_status_code = 'described'
                      and embedding.post_content_image_region_embedding_id is null
               ))
               or ($3::boolean and exists (
                   select 1
                     from post_content_unit unit
                     left join post_content_unit_structure structure
                       on structure.post_content_unit_id = unit.post_content_unit_id
                    where unit.post_id = post.post_id
                      and unit.unit_kind_code <> 'image'
                      and (
                          structure.post_content_unit_structure_id is null
                          or structure.decision_source_code = 'unresolved'
                      )
               ))
               or ($3::boolean and not exists (
                   select 1
                     from operations_case_analysis analysis
                    where analysis.post_id = post.post_id
                      and analysis.source_body_sha256 = job.source_body_sha256
               ))
               or ($3::boolean and not exists (
                   select 1
                     from post_product_analysis analysis
                    where analysis.post_id = post.post_id
                      and analysis.source_body_sha256 = job.source_body_sha256
               ))
           )
         order by case
                      when $3::boolean
                       and exists (
                           select 1
                             from post_project_mention project
                            where project.post_id = post.post_id
                              and nullif(btrim(project.ontology_iri), '') is not null
                       )
                       and not exists (
                           select 1
                             from operations_case_analysis analysis
                            where analysis.post_id = post.post_id
                              and analysis.source_body_sha256 = job.source_body_sha256
                       )
                      then 0 else 1
                  end,
                  coalesce(post.event_occurred_at, post.created_at),
                  post.created_at,
                  post.post_id
         limit $4
         for update of post skip locked
    """
    requests: list[PostContentJobRequest] = []
    async with pool.acquire() as conn:
        async with conn.transaction():
            # Safe SQL: the eligibility predicate is an immutable schema fragment; values are bound.
            rows = await conn.fetch(  # nosemgrep: python.lang.security.audit.sqli.asyncpg-sqli.asyncpg-sqli
                query,
                SUCCEEDED,
                require_embedding,
                require_structure,
                limit,
            )
            for row in rows:
                post_id = str(row["post_id"])
                body = str(row["post_body"] or "")
                complete = await post_content_is_complete(
                    conn,
                    post_id,
                    require_embedding=require_embedding,
                    require_structure=require_structure,
                )
                if complete and require_structure:
                    complete = bool(
                        await conn.fetchval(
                            "select exists (select 1 from operations_case_analysis "
                            "where post_id = $1 and source_body_sha256 = $2) "
                            "and exists (select 1 from post_product_analysis "
                            "where post_id = $1 and source_body_sha256 = $2)",
                            post_id,
                            source_body_sha256(body),
                        )
                    )
                request = await ensure_post_content_job(
                    conn,
                    post_id,
                    body,
                    content_complete=complete,
                )
                if request.should_publish:
                    requests.append(request)

    published = 0
    for request in requests:
        if await publish_post_content_event(
            client,
            post_id=request.post_id,
            source_body_digest=request.source_body_sha256,
        ):
            published += 1
    return {
        "selected_posts": len(rows),
        "queued_posts": len(requests),
        "published_events": published,
        "recovery_pending": len(requests) - published,
    }


async def requeue_failed_post_content_job(
    conn: asyncpg.Connection,
    post_id: str,
    body: str,
) -> PostContentJobRequest:
    """Explicitly requeue one terminal job without weakening automatic retry limits."""
    digest = source_body_sha256(body)
    row = await conn.fetchrow(
        """
        select status_code
        from post_content_ingestion_job
        where post_id = $1
        for update
        """,
        post_id,
    )
    if row is None:
        raise ValueError(f"post-content job does not exist: {post_id}")
    if str(row["status_code"]) != FAILED:
        raise ValueError("only a failed post-content job can be explicitly requeued")
    await conn.execute(
        """
        update post_content_ingestion_job
        set source_body_sha256 = $2,
            status_code = $3,
            attempt_count = 0,
            queued_at = now(),
            next_attempt_at = null,
            started_at = null,
            completed_at = null,
            updated_at = now(),
            last_error_code = null,
            last_error_detail = null
        where post_id = $1
          and status_code = $4
        """,
        post_id,
        digest,
        QUEUED,
        FAILED,
    )
    await _record_status(
        conn,
        post_id,
        QUEUED,
        detail_text="operator requested an explicit post-content retry",
    )
    return PostContentJobRequest(post_id, digest, QUEUED, True)


async def record_post_content_backfill_success(
    conn: asyncpg.Connection,
    post_id: str,
    body: str,
) -> PostContentJobRequest:
    """Synchronize a completed operator backfill with the durable job ledger."""
    digest = source_body_sha256(body)
    row = await conn.fetchrow(
        """
        select status_code
        from post_content_ingestion_job
        where post_id = $1
        for update
        """,
        post_id,
    )
    if row is not None and str(row["status_code"]) in {QUEUED, RUNNING}:
        raise ValueError("cannot finalize a backfill while the job is active")
    if row is None:
        await conn.execute(
            """
            insert into post_content_ingestion_job
                (post_id, source_body_sha256, status_code, completed_at)
            values ($1, $2, $3, now())
            """,
            post_id,
            digest,
            SUCCEEDED,
        )
    else:
        await conn.execute(
            """
            update post_content_ingestion_job
            set source_body_sha256 = $2,
                status_code = $3,
                started_at = null,
                completed_at = now(),
                next_attempt_at = null,
                updated_at = now(),
                last_error_code = null,
                last_error_detail = null
            where post_id = $1
            """,
            post_id,
            digest,
            SUCCEEDED,
        )
    await _record_status(
        conn,
        post_id,
        SUCCEEDED,
        detail_text="operator backfill persisted post-content evidence",
    )
    return PostContentJobRequest(post_id, digest, SUCCEEDED, False)


async def republish_queued_post_content_jobs(
    client: redis.Redis,
    pool: asyncpg.Pool,
    *,
    limit: int = 100,
) -> int:
    """Recover queued rows and stale running leases when Valkey lost wake-ups."""
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            select post_id, source_body_sha256
            from post_content_ingestion_job
            where (
                status_code = $1
                and (
                    next_attempt_at <= now()
                    or (
                        next_attempt_at is null
                        and (
                            attempt_count = 0
                            or queued_at <= now() - $2::interval
                        )
                    )
                )
            )
               or (
                    status_code = $3
                    and started_at is not null
                    and started_at < now() - $4::interval
               )
            order by queued_at
            limit $5
            """,
            QUEUED,
            POST_CONTENT_RETRY_INTERVAL,
            RUNNING,
            STALE_RUNNING_INTERVAL,
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
