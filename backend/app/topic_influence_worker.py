"""Produce persisted topic influence through the external Rust authority."""

from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Callable

import asyncpg

from lineageweave.http_client import HttpAdmissionDeferred, HttpClientError
from lineageweave.topic_influence_client import (
    TopicInfluenceClient,
    TopicInfluenceInvalidResponse,
    TopicInfluenceNotAvailable,
    TopicInfluenceRequest,
    TopicInfluenceResult,
    build_topic_influence_request,
)

_logger = logging.getLogger(__name__)


class TopicInfluenceInputChanged(RuntimeError):
    """The source evidence changed after the external computation began."""


class TopicInfluenceLeaseLost(RuntimeError):
    """A different worker already owns or completed the claimed lease."""


def _iso(value: object) -> str:
    """Return a timezone-bearing ISO timestamp from trusted database evidence."""
    if not isinstance(value, datetime):
        raise ValueError("topic influence timestamp evidence is missing")
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).isoformat()


async def load_topic_influence_request(
    conn: asyncpg.Connection, topic_model_run_id: str
) -> TopicInfluenceRequest:
    """Load one exact TEPP artifact and its normalized membership evidence."""
    model = await conn.fetchrow(
        """
        select model.topic_model_run_id, model.tepp_run_id,
               model.tepp_artifact_sha256, model.posterior_draw_set_id,
               model.posterior_draw_count, model.coordinate_kind_code,
               snapshot.snapshot_sha256, analysis.knowledge_cutoff,
               terminal.remote_run_id as terminal_remote_run_id,
               terminal.result_sha256, receipt.remote_run_id as receipt_remote_run_id
          from topic_model_run model
          join analysis_run analysis on analysis.analysis_run_id = model.analysis_run_id
          join analysis_source_snapshot snapshot
            on snapshot.analysis_source_snapshot_id = analysis.analysis_source_snapshot_id
          join analysis_run_topic_lineage_result terminal
            on terminal.analysis_run_id = analysis.analysis_run_id
          join analysis_run_tepp_receipt receipt
            on receipt.analysis_run_id = analysis.analysis_run_id
         where model.topic_model_run_id = $1
           and model.tepp_schema_version = 'tepp.topic_context_posterior.v1'
           and terminal.remote_run_id = model.tepp_run_id
           and receipt.remote_run_id = model.tepp_run_id
           and terminal.result_sha256 = model.tepp_artifact_sha256
        """,
        topic_model_run_id,
    )
    if model is None:
        raise ValueError("TEPP independent topic artifact is not bound")
    topics = [
        int(row["topic_index"])
        for row in await conn.fetch(
            """
            select topic_index
              from topic_definition
             where topic_model_run_id = $1
             order by topic_index
            """,
            topic_model_run_id,
        )
    ]
    posts = await conn.fetch(
        """
        select distinct membership.source_post_id,
               coalesce(post.event_occurred_at, post.created_at) as event_time
          from topic_context_membership membership
          join source_post post on post.post_id = membership.source_post_id
         where membership.topic_model_run_id = $1
         order by membership.source_post_id
        """,
        topic_model_run_id,
    )
    has_unbound_membership = await conn.fetchval(
        """
        select exists (
            select 1
              from topic_context_membership membership
              left join provenance_assertion assertion
                on assertion.assertion_id = membership.provenance_assertion_id
               and assertion.relation_code = 'prov_was_derived_from'
              left join provenance_resource_binding evidence
                on evidence.resource_id = assertion.object_resource_id
               and evidence.node_type_code = 'node_post'
               and evidence.node_id = membership.source_post_id
             where membership.topic_model_run_id = $1
               and (assertion.assertion_id is null or evidence.resource_id is null)
        )
        """,
        topic_model_run_id,
    )
    if has_unbound_membership:
        raise ValueError("topic membership provenance is incomplete")
    observations: list[dict[str, Any]] = []
    for post in posts:
        post_id = str(post["source_post_id"])
        coordinates = [
            {
                "topic_index": int(row["topic_index"]),
                "posterior_draw_ordinal": int(row["posterior_draw_ordinal"]),
                "value": float(row["coordinate_value"]),
            }
            for row in await conn.fetch(
                """
                select topic_index, posterior_draw_ordinal, coordinate_value
                  from topic_post_coordinate
                 where topic_model_run_id = $1 and source_post_id = $2
                 order by topic_index, posterior_draw_ordinal
                """,
                topic_model_run_id,
                post["source_post_id"],
            )
        ]
        memberships = [
            {
                "membership_id": str(row["topic_context_membership_id"]),
                "dimension_code": row["dimension_code"],
                "context_id": row["context_id"],
                "weight": float(row["membership_weight"]),
                "valid_from": _iso(row["valid_from"]),
                "valid_to": _iso(row["valid_to"]),
                "evidence_sha256": row["evidence_sha256"],
                "provenance_assertion_id": str(row["provenance_assertion_id"]),
            }
            for row in await conn.fetch(
                """
                select membership.topic_context_membership_id,
                       membership.dimension_code, membership.context_id,
                       membership.membership_weight, membership.valid_from,
                       membership.valid_to, membership.evidence_sha256,
                       membership.provenance_assertion_id
                  from topic_context_membership membership
                  join provenance_assertion assertion
                    on assertion.assertion_id = membership.provenance_assertion_id
                   and assertion.relation_code = 'prov_was_derived_from'
                  join provenance_resource_binding evidence
                    on evidence.resource_id = assertion.object_resource_id
                   and evidence.node_type_code = 'node_post'
                   and evidence.node_id = membership.source_post_id
                 where membership.topic_model_run_id = $1
                   and membership.source_post_id = $2
                 order by membership.dimension_code, membership.context_id,
                          membership.topic_context_membership_id
                """,
                topic_model_run_id,
                post["source_post_id"],
            )
        ]
        observations.append(
            {
                "post_id": post_id,
                "event_time": _iso(post["event_time"]),
                "coordinates": coordinates,
                "memberships": memberships,
            }
        )
    return build_topic_influence_request(
        tepp_run={
            "tepp_run_id": model["tepp_run_id"],
            "tepp_artifact_sha256": model["tepp_artifact_sha256"],
            "source_snapshot_sha256": model["snapshot_sha256"],
            "knowledge_cutoff": _iso(model["knowledge_cutoff"]),
            "posterior_draw_set_id": model["posterior_draw_set_id"],
            "posterior_draw_count": int(model["posterior_draw_count"]),
            "coordinate_kind_code": model["coordinate_kind_code"],
            "topic_model_run_id": str(model["topic_model_run_id"]),
        },
        topics=topics,
        observations=observations,
    )


async def claim_topic_influence_job(
    pool: asyncpg.Pool,
    lease_timeout_seconds: int,
) -> tuple[str, TopicInfluenceRequest, str] | None:
    """Lease the first complete queued request without holding provider I/O open."""
    async with pool.acquire() as conn:
        await conn.execute(
            """
            update topic_influence_job
               set status_code = 'queued', started_at = null,
                   lease_expires_at = null, completed_at = null,
                   lease_token = null, failure_code = null,
                   request_sha256 = null,
                   not_before = clock_timestamp()
             where status_code = 'running'
               and lease_expires_at <= clock_timestamp()
            """
        )
        candidates = await conn.fetch(
            """
            select topic_model_run_id
             from topic_influence_job
             where status_code = 'queued'
               and not_before <= clock_timestamp()
             order by queued_at, topic_model_run_id
            """
        )
        for candidate in candidates:
            run_id = str(candidate["topic_model_run_id"])
            try:
                request = await load_topic_influence_request(conn, run_id)
            except (ValueError, TypeError, KeyError):
                await conn.execute(
                    """
                    update topic_influence_job
                       set status_code = 'awaiting_evidence',
                           failure_code = 'input_evidence_incomplete',
                           completed_at = clock_timestamp()
                     where topic_model_run_id = $1 and status_code = 'queued'
                    """,
                    run_id,
                )
                continue
            async with conn.transaction():
                lease_token = str(uuid.uuid4())
                claimed = await conn.fetchval(
                    """
                    update topic_influence_job
                       set status_code = 'running', request_sha256 = $2,
                           attempt_count = attempt_count + 1,
                           started_at = clock_timestamp(), completed_at = null,
                           failure_code = null,
                           lease_token = $4::uuid,
                           lease_expires_at = clock_timestamp()
                               + make_interval(secs => $3)
                     where topic_model_run_id = $1 and status_code = 'queued'
                    returning topic_model_run_id
                    """,
                    run_id,
                    request.request_sha256,
                    lease_timeout_seconds,
                    lease_token,
                )
            if claimed is not None:
                return run_id, request, lease_token
    return None


async def persist_topic_influence_result(
    pool: asyncpg.Pool,
    topic_model_run_id: str,
    request: TopicInfluenceRequest,
    result: TopicInfluenceResult,
    lease_token: str,
) -> None:
    """Persist one complete result after rechecking the current input digest."""
    payload = result.payload
    async with pool.acquire() as conn:
        async with conn.transaction():
            job = await conn.fetchrow(
                """
                select request_sha256, lease_token::text as lease_token
                  from topic_influence_job
                 where topic_model_run_id = $1 and status_code = 'running'
                 for update
                """,
                topic_model_run_id,
            )
            if (
                job is None
                or job["request_sha256"] != request.request_sha256
                or job["lease_token"] != lease_token
            ):
                raise TopicInfluenceLeaseLost(
                    "topic influence job lease no longer matches"
                )
            try:
                current = await load_topic_influence_request(conn, topic_model_run_id)
            except ValueError as exc:
                raise TopicInfluenceInputChanged(
                    "topic influence evidence became incomplete during computation"
                ) from exc
            if current.request_sha256 != request.request_sha256:
                raise TopicInfluenceInputChanged(
                    "topic influence input changed during computation"
                )
            influence_run_id = await conn.fetchval(
                """
                insert into topic_influence_run
                    (topic_model_run_id, fast_mlsirm_schema_version,
                     fast_mlsirm_version, fast_mlsirm_code_revision,
                     fast_mlsirm_artifact_sha256, reported_tepp_run_id,
                     reported_snapshot_sha256, reported_knowledge_cutoff,
                     membership_fingerprint_sha256, compute_backend_code,
                     precision_code, posterior_draw_coverage,
                     convergence_status_code, identification_status_code,
                     parity_status_code)
                values ($1, $2, $3, $4, $5, $6, $7, $8::timestamptz, $9,
                        $10, $11, $12, $13, $14, $15)
                returning topic_influence_run_id
                """,
                topic_model_run_id,
                payload["schema_version"],
                payload["producer_version"],
                payload["code_revision"],
                payload["artifact_sha256"],
                payload["tepp_run_id"],
                payload["source_snapshot_sha256"],
                payload["knowledge_cutoff"],
                payload["membership_fingerprint_sha256"],
                payload["compute_backend_code"],
                payload["precision_code"],
                payload["posterior_draw_coverage"],
                payload["convergence_status_code"],
                payload["identification_status_code"],
                payload["parity_status_code"],
            )
            for influence in payload["influences"]:
                await conn.execute(
                    """
                    insert into topic_post_context_influence
                        (topic_model_run_id, topic_influence_run_id,
                         topic_context_membership_id, topic_index,
                         influence_value, uncertainty_method_code,
                         uncertainty_lower_value, uncertainty_upper_value,
                         diagnostic_status_code)
                    values ($1, $2, $3::uuid, $4, $5, $6, $7, $8, $9)
                    """,
                    topic_model_run_id,
                    influence_run_id,
                    influence["membership_id"],
                    influence["topic_index"],
                    influence["influence_value"],
                    influence["uncertainty_method_code"],
                    influence["uncertainty_lower_value"],
                    influence["uncertainty_upper_value"],
                    influence["diagnostic_status_code"],
                )
            await conn.execute(
                """
                update topic_influence_job
                   set status_code = 'succeeded', completed_at = clock_timestamp(),
                       lease_expires_at = null, lease_token = null
                 where topic_model_run_id = $1 and status_code = 'running'
                   and lease_token = $2::uuid
                """,
                topic_model_run_id,
                lease_token,
            )


async def _fail_job(
    pool: asyncpg.Pool, run_id: str, lease_token: str, failure_code: str
) -> None:
    """Record a bounded failure without persisting provider content."""
    async with pool.acquire() as conn:
        await conn.execute(
            """
            update topic_influence_job
               set status_code = 'failed', failure_code = $3,
                   completed_at = clock_timestamp(), lease_expires_at = null,
                   lease_token = null, request_sha256 = null
             where topic_model_run_id = $1 and status_code = 'running'
               and lease_token = $2::uuid
            """,
            run_id,
            lease_token,
            failure_code,
        )


async def _defer_job(
    pool: asyncpg.Pool, run_id: str, lease_token: str, retry_after_seconds: int
) -> None:
    """Requeue a remotely deferred job at the exact admitted retry instant."""
    async with pool.acquire() as conn:
        await conn.execute(
            """
            update topic_influence_job
               set status_code = 'queued', started_at = null, completed_at = null,
                   failure_code = null,
                   not_before = clock_timestamp() + make_interval(secs => $3),
                   lease_expires_at = null, lease_token = null,
                   request_sha256 = null
             where topic_model_run_id = $1 and status_code = 'running'
               and lease_token = $2::uuid
            """,
            run_id,
            lease_token,
            retry_after_seconds,
        )


async def requeue_topic_influence_job(pool: asyncpg.Pool, run_id: str) -> bool:
    """Explicitly requeue one failed job after an operator resolves its cause."""
    async with pool.acquire() as conn:
        updated = await conn.fetchval(
            """
            update topic_influence_job
               set status_code = 'queued', started_at = null, completed_at = null,
                   failure_code = null, not_before = clock_timestamp(),
                   lease_expires_at = null, lease_token = null,
                   request_sha256 = null
             where topic_model_run_id = $1 and status_code = 'failed'
            returning topic_model_run_id
            """,
            run_id,
        )
    return updated is not None


async def _release_changed_job(
    pool: asyncpg.Pool, run_id: str, lease_token: str
) -> None:
    """Release a stale lease so the next claim rebuilds the changed request."""
    async with pool.acquire() as conn:
        await conn.execute(
            """
            update topic_influence_job
               set status_code = 'queued', started_at = null, completed_at = null,
                   failure_code = null, not_before = clock_timestamp(),
                   lease_expires_at = null, lease_token = null,
                   request_sha256 = null
             where topic_model_run_id = $1 and status_code = 'running'
               and lease_token = $2::uuid
            """,
            run_id,
            lease_token,
        )


async def process_topic_influence_job(
    pool: asyncpg.Pool, client: TopicInfluenceClient
) -> bool:
    """Produce at most one queued result and return whether work was claimed."""
    claimed = await claim_topic_influence_job(pool, client.lease_timeout_seconds)
    if claimed is None:
        return False
    run_id, request, lease_token = claimed
    try:
        result = await asyncio.to_thread(client.estimate, request)
        await persist_topic_influence_result(
            pool, run_id, request, result, lease_token
        )
    except HttpAdmissionDeferred as exc:
        await _defer_job(pool, run_id, lease_token, exc.retry_after_seconds)
    except TopicInfluenceInputChanged:
        await _release_changed_job(pool, run_id, lease_token)
    except TopicInfluenceLeaseLost:
        _logger.info("Topic influence lease changed before result persistence")
    except (TopicInfluenceNotAvailable, HttpClientError, OSError, TimeoutError):
        await _fail_job(pool, run_id, lease_token, "producer_unavailable")
    except TopicInfluenceInvalidResponse:
        await _fail_job(pool, run_id, lease_token, "producer_result_invalid")
    except Exception:  # noqa: BLE001 - failure is bounded and the worker continues.
        _logger.exception("topic influence production failed")
        await _fail_job(pool, run_id, lease_token, "persistence_failed")
    return True


async def run_topic_influence_worker(
    pool: asyncpg.Pool,
    client_factory: Callable[[], TopicInfluenceClient],
    *,
    poll_seconds: float,
) -> None:
    """Poll the durable lease table and keep the shared worker responsive."""
    while True:
        try:
            worked = await process_topic_influence_job(pool, client_factory())
        except (asyncpg.PostgresError, OSError, TimeoutError):
            _logger.exception(
                "Topic influence could not claim database work; verify database "
                "connectivity before the next poll"
            )
            await asyncio.sleep(poll_seconds)
            continue
        if not worked:
            await asyncio.sleep(poll_seconds)
