"""Start a Pending lineage reconstruction or TEPP measurement.

ADR 0021 reconstructs lineage. ADR 0022 starts TEPP through
``tepp_client`` only. ADR 0023 enqueues that work on a durable outbox
so a crash after Running does not lose the item. ADR 0162 persists a
TEPP accepted envelope as transport evidence and keeps the local run
Running. Period-report stays another path. Neither start invents a
theta or a calibrated report score.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlparse
from uuid import UUID

import asyncpg

from backend.app.analysis_run_ingestion import (
    AnalysisRunCreateError,
    fetch_tepp_accepted_receipt,
    fetch_visible_analysis_run,
)
from backend.app.post_eligibility import SOURCE_POST_ELIGIBILITY_SQL
from backend.app.analysis_run_outbox import (
    latest_outbox_delivery_is_claimed,
    latest_outbox_delivery_is_delivered,
    outbox_request_digest,
)
from backend.app.lineage_ingestion import records_from_source_posts
from lineageweave.adjudication_client import AdjudicationClient
from lineageweave.http_client import HttpClientError, post_json
from lineageweave.lineage_persistence import lineage_edge_specs
from lineageweave.models import Edge
from lineageweave.tepp_client import (
    AnalysisRunRequest,
    TeppClient,
    TeppInvalidResponse,
    TeppNotAvailable,
)

_LINEAGE_KIND = "analysis_run_lineage"
_TEPP_KIND = "analysis_run_tepp"
_REPORT_KIND = "analysis_run_report"
_PENDING = "analysis_status_pending"
_RUNNING = "analysis_status_running"
_SUCCEEDED = "analysis_status_succeeded"
_FAILED = "analysis_status_failed"
_TEPP_MODEL_CONTRACT = "tepp-analysis-run-v1"
_TEPP_OUTPUT_PROFILE = "calibrated_event_measurement"
_TEPP_TRANSPORT_STATES = frozenset({"accepted", "queued", "running"})
_TEPP_COMPLETED_STATES = frozenset({"completed", "succeeded"})
_PERSIST_RESULT = "result"
_PERSIST_RECEIPT = "receipt"


class AnalysisRunStartError(AnalysisRunCreateError):
    """Fail-closed start: HTTP status plus a next-action detail string."""


@dataclass(frozen=True)
class TeppSubmissionOutcome:
    """Classified TEPP envelope: local status, optional persist kind.

    ``persist_kind`` is ``result`` (completed measurement), ``receipt``
    (accepted transport evidence), or empty when nothing may be stored.
    A receipt is never a measurement and never invents a theta.
    """

    status_code: str
    failure_code: str
    envelope: dict[str, Any] | None
    persist_kind: str


def reconstruction_result_digest(edges: list[Edge]) -> str:
    """SHA-256 of the ordered parent choices. Never hashes a post body."""
    material = json.dumps(
        [
            {
                "child_post_id": edge.child_id,
                "fused_score": round(float(edge.fused_score), 6),
                "parent_post_id": edge.parent_id,
            }
            for edge in sorted(edges, key=lambda item: (item.child_id, item.parent_id))
        ],
        separators=(",", ":"),
        sort_keys=True,
    )
    return hashlib.sha256(material.encode()).hexdigest()


def start_kind_rejection(run_kind_code: str) -> AnalysisRunStartError | None:
    """Return a 422 when start cannot run this kind.

    Lineage reconstructs the frozen bag. TEPP submits through
    ``tepp_client`` and never invents a theta. Period-report stays on
    its own rebuild path.
    """
    if run_kind_code in {_LINEAGE_KIND, _TEPP_KIND}:
        return None
    if run_kind_code == _REPORT_KIND:
        return AnalysisRunStartError(
            422,
            "Rebuild the period report from the reports panel. "
            "This start path does not invent a measurement.",
        )
    return AnalysisRunStartError(
        422,
        "Start reconstructs a Pending lineage run or submits TEPP. "
        "This start path does not invent a measurement.",
    )


def configured_tepp_client(
    transport_url: str = "",
    api_key: str = "",
    temporal_context_url: str = "",
) -> TeppClient:
    """Build a TEPP client from an optional HTTP transport URL.

    An empty URL keeps the default unavailable transport. A set URL
    POSTs TEPP's published wire payload. File URLs and other schemes
    stay unavailable -- this is not a local psychometric substitute.
    """
    url = transport_url.strip()
    temporal_url = temporal_context_url.strip()
    if not url and not temporal_url:
        return TeppClient()

    def unavailable_transport(_payload: dict[str, Any]) -> dict[str, Any]:
        """Fail closed when only a temporal-context TEPP endpoint exists."""
        raise TeppNotAvailable("TEPP analysis-run transport unavailable")

    def transport(payload: dict[str, Any]) -> dict[str, Any]:
        """Submit an analysis-run request through the configured TEPP endpoint."""
        try:
            headers = {
                "tepp-consumer": "lineageweave",
                "tepp-contract-version": "1",
                "idempotency-key": str(payload["idempotency_key"]),
            }
            return post_json(
                url,
                payload,
                headers=headers,
                timeout=30.0,
                include_context_metadata=False,
            )
        except (HttpClientError, OSError, ValueError, TypeError) as exc:
            raise TeppNotAvailable("TEPP transport unavailable") from exc

    def temporal_transport(payload: dict[str, Any]) -> dict[str, Any]:
        """Submit a temporal-context request through the configured TEPP endpoint."""
        if not temporal_url:
            raise TeppNotAvailable("TEPP temporal-context transport unavailable")
        try:
            headers = {"tepp-consumer": "lineageweave", "tepp-contract-version": "1"}
            if urlparse(temporal_url).hostname == "host.docker.internal":
                headers["host"] = "127.0.0.1"
            return post_json(
                temporal_url,
                payload,
                headers=headers,
                timeout=10.0,
                include_context_metadata=False,
            )
        except (HttpClientError, OSError, ValueError, TypeError) as exc:
            raise TeppNotAvailable("TEPP temporal-context transport unavailable") from exc

    return TeppClient(
        transport=transport if url else unavailable_transport,
        temporal_transport=temporal_transport,
    )


def tepp_run_request(
    *,
    idempotency_key: str,
    snapshot_sha256: str,
    knowledge_cutoff: datetime,
    corporate_entity_id: str,
) -> AnalysisRunRequest:
    """Build TEPP's published request from the frozen run, never a theta."""
    cutoff = knowledge_cutoff
    if cutoff.tzinfo is None:
        cutoff = cutoff.replace(tzinfo=timezone.utc)
    return AnalysisRunRequest(
        idempotency_key=idempotency_key,
        tenant_workspace_id=str(corporate_entity_id),
        snapshot_id=snapshot_sha256,
        knowledge_cutoff=cutoff.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        model_contract_version=_TEPP_MODEL_CONTRACT,
        output_profile=_TEPP_OUTPUT_PROFILE,
    )


def tepp_envelope_status(envelope: dict[str, Any]) -> str:
    """Normalize TEPP ``status`` or ``run_state``. Empty when neither is a string."""
    raw = envelope.get("status")
    if not isinstance(raw, str) or not raw.strip():
        raw = envelope.get("run_state")
    if isinstance(raw, str):
        return raw.strip().casefold()
    return ""


def tepp_remote_run_id(envelope: dict[str, Any]) -> str:
    """Remote run identity from TEPP's published envelope keys."""
    for key in ("analysis_run_id", "run_id", "remote_run_id"):
        value = envelope.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


def tepp_accepted_status_code(envelope: dict[str, Any]) -> str:
    """Transport state when the envelope is accepted/queued/running."""
    status = tepp_envelope_status(envelope)
    return status if status in _TEPP_TRANSPORT_STATES else ""


def tepp_request_digest(request: AnalysisRunRequest) -> str:
    """SHA-256 of the published seven-field request. Never hashes a theta."""
    material = json.dumps(request.to_json(), separators=(",", ":"), sort_keys=True)
    return hashlib.sha256(material.encode("utf-8")).hexdigest()


def tepp_receipt_digest(
    *,
    remote_run_id: str,
    accepted_status_code: str,
    model_contract_version: str,
    snapshot_id: str,
    knowledge_cutoff: str,
) -> str:
    """SHA-256 of persisted receipt columns. Never hashes a result body."""
    material = json.dumps(
        {
            "accepted_status_code": accepted_status_code,
            "knowledge_cutoff": knowledge_cutoff,
            "model_contract_version": model_contract_version,
            "remote_run_id": remote_run_id,
            "snapshot_id": snapshot_id,
        },
        separators=(",", ":"),
        sort_keys=True,
    )
    return hashlib.sha256(material.encode("utf-8")).hexdigest()


def classify_tepp_submission(
    client: TeppClient,
    request: AnalysisRunRequest,
) -> TeppSubmissionOutcome:
    """Classify a TEPP envelope without inventing a measurement.

    Accepted/queued/running with a remote run id is transport evidence.
    Only a completed envelope with a result dict may persist a
    measurement. An empty accepted envelope stays unpersistable.
    """
    try:
        response = client.submit_analysis_run(request)
    except TeppNotAvailable:
        return TeppSubmissionOutcome(_FAILED, "tepp_not_available", None, "")
    if not isinstance(response, dict):
        return TeppSubmissionOutcome(_FAILED, "tepp_result_not_persisted", None, "")
    status = tepp_envelope_status(response)
    remote_run_id = tepp_remote_run_id(response)
    if status in _TEPP_COMPLETED_STATES:
        if isinstance(response.get("result"), dict) and remote_run_id:
            return TeppSubmissionOutcome(_SUCCEEDED, "", response, _PERSIST_RESULT)
        return TeppSubmissionOutcome(_FAILED, "tepp_result_not_persisted", None, "")
    if status in _TEPP_TRANSPORT_STATES:
        if remote_run_id:
            return TeppSubmissionOutcome(_RUNNING, "", response, _PERSIST_RECEIPT)
        return TeppSubmissionOutcome(_FAILED, "tepp_result_not_persisted", None, "")
    return TeppSubmissionOutcome(_FAILED, "tepp_result_not_persisted", None, "")


def classify_tepp_status(
    client: TeppClient,
    request: AnalysisRunRequest,
    remote_run_id: str,
) -> TeppSubmissionOutcome:
    """Read one bounded, request-bound TEPP status without resubmitting work."""
    try:
        response = client.read_analysis_run_status(remote_run_id, request)
    except TeppNotAvailable:
        return TeppSubmissionOutcome(_RUNNING, "", None, "")
    except TeppInvalidResponse:
        return TeppSubmissionOutcome(_FAILED, "tepp_result_not_persisted", None, "")
    state = response["run_state"]
    if state in {"accepted", "running"}:
        return TeppSubmissionOutcome(_RUNNING, "", response, "")
    terminal = response["terminal_result"]
    if state == "failed":
        return TeppSubmissionOutcome(
            _FAILED,
            str(terminal["failure_code"]),
            terminal,
            "",
        )
    return TeppSubmissionOutcome(_SUCCEEDED, "", terminal, _PERSIST_RESULT)


def _tepp_submission(
    client: TeppClient,
    request: AnalysisRunRequest,
) -> tuple[str, str, dict[str, Any] | None]:
    """Compatibility projection used by older start tests."""
    outcome = classify_tepp_submission(client, request)
    return outcome.status_code, outcome.failure_code, outcome.envelope


def tepp_submit_outcome(
    client: TeppClient,
    request: AnalysisRunRequest,
) -> tuple[str, str]:
    """Compatibility projection of the TEPP submission outcome."""
    outcome = classify_tepp_submission(client, request)
    return outcome.status_code, outcome.failure_code


async def _persist_tepp_result(
    conn: asyncpg.Connection,
    *,
    analysis_run_id: str,
    envelope: dict[str, Any],
) -> bool:
    """Persist only a validated, remote-completed TEPP envelope."""
    remote_run_id = tepp_remote_run_id(envelope)
    if not remote_run_id:
        return False
    result_json = json.dumps(envelope, separators=(",", ":"), sort_keys=True)
    result_sha256 = hashlib.sha256(result_json.encode("utf-8")).hexdigest()
    try:
        async with conn.transaction():
            existing = await conn.fetchrow(
                """
                select remote_run_id, result_sha256
                from analysis_run_tepp_result
                where analysis_run_id = $1
                """,
                analysis_run_id,
            )
            if existing is not None:
                return (
                    str(existing["remote_run_id"]) == remote_run_id
                    and str(existing["result_sha256"]) == result_sha256
                )
            await conn.execute(
                """
                insert into analysis_run_tepp_result
                    (analysis_run_id, remote_run_id, result_json, result_sha256)
                values ($1, $2, $3::jsonb, $4)
                on conflict (analysis_run_id) do nothing
                """,
                analysis_run_id,
                remote_run_id,
                result_json,
                result_sha256,
            )
    except (asyncpg.PostgresError, TypeError, ValueError):
        return False
    return True


async def _persist_tepp_accepted_receipt(
    conn: asyncpg.Connection,
    *,
    analysis_run_id: str,
    envelope: dict[str, Any],
    request: AnalysisRunRequest,
    knowledge_cutoff: datetime,
) -> bool:
    """Persist transport evidence. Never writes a result or a theta."""
    remote_run_id = tepp_remote_run_id(envelope)
    accepted_status_code = tepp_accepted_status_code(envelope)
    if not remote_run_id or not accepted_status_code:
        return False
    cutoff = knowledge_cutoff
    if cutoff.tzinfo is None:
        cutoff = cutoff.replace(tzinfo=timezone.utc)
    cutoff_iso = cutoff.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    request_sha256 = tepp_request_digest(request)
    receipt_sha256 = tepp_receipt_digest(
        remote_run_id=remote_run_id,
        accepted_status_code=accepted_status_code,
        model_contract_version=request.model_contract_version,
        snapshot_id=request.snapshot_id,
        knowledge_cutoff=cutoff_iso,
    )
    try:
        async with conn.transaction():
            existing = await conn.fetchrow(
                """
                select remote_run_id, request_sha256
                from analysis_run_tepp_accepted_receipt
                where analysis_run_id = $1
                """,
                analysis_run_id,
            )
            if existing is not None:
                return (
                    str(existing["remote_run_id"]) == remote_run_id
                    and str(existing["request_sha256"]) == request_sha256
                )
            # Safe SQL: fixed insert text; every external value is bound as $1 through $8.
            await conn.execute(  # nosemgrep: python.django.security.injection.sql.sql-injection-using-db-cursor-execute.sql-injection-db-cursor-execute, python.lang.security.audit.sqli.asyncpg-sqli.asyncpg-sqli -- code-scanning alert 226
                """
                insert into analysis_run_tepp_accepted_receipt
                    (analysis_run_id, remote_run_id, request_sha256, receipt_sha256,
                     accepted_status_code, model_contract_version, snapshot_id,
                     knowledge_cutoff)
                values ($1, $2, $3, $4, $5, $6, $7, $8)
                """,
                analysis_run_id,
                remote_run_id,
                request_sha256,
                receipt_sha256,
                accepted_status_code,
                request.model_contract_version,
                request.snapshot_id,
                cutoff,
            )
    except asyncpg.UndefinedTableError:
        return False
    except (asyncpg.PostgresError, TypeError, ValueError):
        return False
    return True


def start_write_conflict_error() -> AnalysisRunStartError:
    """Next action when a concurrent start already wrote this run."""
    return AnalysisRunStartError(
        409,
        "Open this run. Refresh to see the stored tree if start already finished.",
    )


def reconstruction_member_ids(
    snapshot_member_ids: list[str],
    cutoff_post_ids: list[str],
) -> list[str]:
    """Prefer create-time membership over a later cutoff re-query.

    An empty member list means this database has not frozen the bag yet
    (migration 0022 missing, or a legacy snapshot). Start then uses the
    live cutoff query so those rows still reconstruct.
    """
    if snapshot_member_ids:
        return list(snapshot_member_ids)
    return list(cutoff_post_ids)


async def _cutoff_source_posts(
    conn: asyncpg.Connection,
    *,
    corporate_entity_id: Any,
    knowledge_cutoff: Any,
    affiliated_entity_ids: list[str],
) -> list[asyncpg.Record]:
    """ABAC-visible cutoff rows with the grouping keys reconstruct needs."""
    # Safe SQL: the eligibility predicate is an immutable schema fragment; both request values are bound.
    rows = await conn.fetch(  # nosemgrep: python.lang.security.audit.sqli.asyncpg-sqli.asyncpg-sqli
        f"""
        select post_id, post_title, created_at, visibility_code,
               corporate_entity_id, process_unit_id,
               thread_group_key, secondary_grouping_key
        from source_post
        where corporate_entity_id = $1
          and created_at <= $2
          and {SOURCE_POST_ELIGIBILITY_SQL.format(alias="source_post")}
        order by created_at, post_title
        """,
        corporate_entity_id,
        knowledge_cutoff,
    )
    affiliated = {str(entity_id) for entity_id in affiliated_entity_ids}
    return [
        row
        for row in rows
        if row["visibility_code"] == "public"
        or str(row["corporate_entity_id"]) in affiliated
    ]


async def _snapshot_member_posts(
    conn: asyncpg.Connection,
    snapshot_id: Any,
) -> list[asyncpg.Record]:
    """Load frozen capture rows, or empty when the member table is absent."""
    try:
        return list(
            # Safe SQL: the eligibility predicate is an immutable schema fragment; snapshot id is bound.
            await conn.fetch(  # nosemgrep: python.lang.security.audit.sqli.asyncpg-sqli.asyncpg-sqli
                f"""
                select post.post_id, post.post_title, post.created_at,
                       post.visibility_code, post.corporate_entity_id,
                       post.process_unit_id, post.thread_group_key,
                       post.secondary_grouping_key
                from analysis_source_snapshot_member member
                join source_post post
                  on post.post_id = member.source_post_id
                 and {SOURCE_POST_ELIGIBILITY_SQL.format(alias="post")}
                where member.analysis_source_snapshot_id = $1
                order by post.created_at, post.post_title
                """,
                snapshot_id,
            )
        )
    except asyncpg.UndefinedTableError:
        return []


async def _append_status(
    conn: asyncpg.Connection,
    analysis_run_id: str,
    status_ordinal: int,
    status_code: str,
    failure_code: str | None = None,
) -> None:
    """Append one legal lifecycle event. Failed rows carry a machine code.

    Occurrence and recording share one PostgreSQL ``clock_timestamp()``
    so ``analysis_run_status_time_check`` cannot see a Python clock that
    is ahead of the trigger write clock (ADR 0171).
    """
    await conn.execute(
        """
        insert into analysis_run_status_event
            (analysis_run_id, status_ordinal, status_code,
             occurred_at, recorded_at, failure_code)
        select $1, $2, $3, write_clock, write_clock, $4
        from (select clock_timestamp() as write_clock) same_clock
        """,
        analysis_run_id,
        status_ordinal,
        status_code,
        failure_code,
    )


async def _next_status_ordinal(
    conn: asyncpg.Connection,
    analysis_run_id: str,
) -> int:
    """Return the next contiguous status ordinal for this run."""
    current_max = await conn.fetchval(
        """
        select coalesce(max(status_ordinal), 0)
        from analysis_run_status_event
        where analysis_run_id = $1
        """,
        analysis_run_id,
    )
    return int(current_max) + 1


async def _latest_outbox_delivery(
    conn: asyncpg.Connection,
    analysis_run_id: str,
) -> str | None:
    """Newest outbox delivery status, or None when the row was never claimed."""
    return await conn.fetchval(
        """
        select delivery_status_code
        from analysis_run_outbox_delivery
        where analysis_run_id = $1
        order by delivery_ordinal desc
        limit 1
        """,
        analysis_run_id,
    )


async def _next_outbox_delivery_ordinal(
    conn: asyncpg.Connection,
    analysis_run_id: str,
) -> int:
    """Return the next contiguous outbox delivery ordinal for this run."""
    current_max = await conn.fetchval(
        """
        select coalesce(max(delivery_ordinal), 0)
        from analysis_run_outbox_delivery
        where analysis_run_id = $1
        """,
        analysis_run_id,
    )
    return int(current_max) + 1


async def _append_outbox_delivery(
    conn: asyncpg.Connection,
    analysis_run_id: str,
    delivery_ordinal: int,
    delivery_status_code: str,
    occurred_at: datetime,
    valkey_stream_entry_id: str | None = None,
) -> None:
    """Append one claim or delivery event. Stream id is optional."""
    await conn.execute(
        """
        insert into analysis_run_outbox_delivery
            (analysis_run_id, delivery_ordinal, delivery_status_code,
             occurred_at, valkey_stream_entry_id)
        values ($1, $2, $3, $4, $5)
        """,
        analysis_run_id,
        delivery_ordinal,
        delivery_status_code,
        occurred_at,
        valkey_stream_entry_id,
    )


async def _visible_or_404(
    conn: asyncpg.Connection,
    analysis_run_id: str,
    account_id: str,
    affiliated_entity_ids: list[str],
) -> dict[str, Any]:
    """Reload the authorized projection or hide the run."""
    started = await fetch_visible_analysis_run(
        conn,
        analysis_run_id,
        account_id,
        affiliated_entity_ids,
    )
    if started is None:
        raise AnalysisRunStartError(404, "This analysis run is not visible.")
    return started


async def _attach_outbox_digest(
    conn: asyncpg.Connection,
    started: dict[str, Any],
) -> dict[str, Any]:
    """Expose the wake-up digest to the start API, never to the client body."""
    digest = await conn.fetchval(
        """
        select request_sha256
        from analysis_run_outbox
        where analysis_run_id = $1
        """,
        started["analysis_run_id"],
    )
    if not digest:
        return started
    attached = dict(started)
    attached["outbox_request_sha256"] = str(digest)
    return attached


async def _lock_start_run(
    conn: asyncpg.Connection,
    analysis_run_id: str,
) -> asyncpg.Record:
    """Lock the run row used by enqueue and delivery."""
    locked = await conn.fetchrow(
        """
        select run.analysis_run_id, run.knowledge_cutoff, run.run_kind_code,
               run.idempotency_key, run.analysis_source_snapshot_id,
               snapshot.snapshot_sha256, scope.corporate_entity_id
        from analysis_run run
        join analysis_run_scope scope on scope.analysis_run_id = run.analysis_run_id
        join analysis_source_snapshot snapshot
          on snapshot.analysis_source_snapshot_id = run.analysis_source_snapshot_id
        where run.analysis_run_id = $1
        for update of run
        """,
        analysis_run_id,
    )
    if locked is None:
        raise AnalysisRunStartError(404, "This analysis run is not visible.")
    return locked


async def enqueue_pending_analysis_run(
    conn: asyncpg.Connection,
    *,
    analysis_run_id: str,
    account_id: str,
    affiliated_entity_ids: list[str],
) -> dict[str, Any]:
    """Append Running and one outbox row, or resume an undelivered item.

    Period-report is rejected so this path cannot invent a calibrated
    score. A Succeeded retry returns the stored reconstruction. A
    Running row with an undelivered outbox is a crash resume. A Running
    row without pending work is 409. Hidden runs 404.
    """
    try:
        UUID(analysis_run_id)
    except ValueError as exc:
        raise AnalysisRunStartError(404, "This analysis run is not visible.") from exc

    current = await fetch_visible_analysis_run(
        conn,
        analysis_run_id,
        account_id,
        affiliated_entity_ids,
    )
    if current is None:
        raise AnalysisRunStartError(404, "This analysis run is not visible.")
    kind_error = start_kind_rejection(current["run_kind_code"])
    if kind_error is not None:
        raise kind_error
    if current["status_code"] == _SUCCEEDED:
        return current

    locked = await _lock_start_run(conn, analysis_run_id)
    locked_status = await conn.fetchval(
        """
        select status_code
        from analysis_run_current_status
        where analysis_run_id = $1
        """,
        analysis_run_id,
    )
    if locked_status == _SUCCEEDED:
        return await _visible_or_404(
            conn, analysis_run_id, account_id, affiliated_entity_ids
        )
    if locked_status == _RUNNING:
        latest = await _latest_outbox_delivery(conn, analysis_run_id)
        if latest_outbox_delivery_is_delivered(latest):
            raise AnalysisRunStartError(
                409,
                "Open this run. Start is only for a Pending lineage reconstruction "
                "or TEPP measurement.",
            )
        has_outbox = await conn.fetchval(
            """
            select 1 from analysis_run_outbox where analysis_run_id = $1
            """,
            analysis_run_id,
        )
        if has_outbox is None:
            raise AnalysisRunStartError(
                409,
                "Open this run. Start is only for a Pending lineage reconstruction "
                "or TEPP measurement.",
            )
        return await _attach_outbox_digest(
            conn,
            await _visible_or_404(
                conn, analysis_run_id, account_id, affiliated_entity_ids
            ),
        )
    if locked_status != _PENDING:
        raise AnalysisRunStartError(
            409,
            "Open this run. Start is only for a Pending lineage reconstruction "
            "or TEPP measurement.",
        )

    now = await conn.fetchval("select clock_timestamp()")
    digest = outbox_request_digest(
        analysis_run_id=str(locked["analysis_run_id"]),
        work_kind_code=str(locked["run_kind_code"]),
        snapshot_sha256=str(locked["snapshot_sha256"]),
        knowledge_cutoff=locked["knowledge_cutoff"],
    )
    try:
        await _append_status(
            conn,
            analysis_run_id,
            await _next_status_ordinal(conn, analysis_run_id),
            _RUNNING,
        )
        await conn.execute(
            """
            insert into analysis_run_outbox
                (analysis_run_id, work_kind_code, request_sha256, enqueued_at)
            values ($1, $2, $3, $4)
            """,
            analysis_run_id,
            locked["run_kind_code"],
            digest,
            now,
        )
    except asyncpg.UniqueViolationError as exc:
        raise start_write_conflict_error() from exc
    return await _attach_outbox_digest(
        conn,
        await _visible_or_404(
            conn, analysis_run_id, account_id, affiliated_entity_ids
        ),
    )


async def deliver_queued_analysis_run(
    conn: asyncpg.Connection,
    *,
    analysis_run_id: str,
    account_id: str,
    affiliated_entity_ids: list[str],
    tepp_client: TeppClient | None = None,
    adjudication_client: AdjudicationClient | None = None,
    valkey_stream_entry_id: str | None = None,
) -> dict[str, Any]:
    """Claim the outbox row and finish ThreadWeave or TEPP.

    A delivered row replays the stored result. Missing work is 409.
    TEPP stays Failed when the transport is missing or the envelope is
    not persistable. An accepted receipt keeps the run Running and
    leaves the outbox claimed. No theta is invented.
    """
    try:
        UUID(analysis_run_id)
    except ValueError as exc:
        raise AnalysisRunStartError(404, "This analysis run is not visible.") from exc

    current = await fetch_visible_analysis_run(
        conn,
        analysis_run_id,
        account_id,
        affiliated_entity_ids,
    )
    if current is None:
        raise AnalysisRunStartError(404, "This analysis run is not visible.")
    if current["status_code"] == _SUCCEEDED:
        return current

    outbox = await conn.fetchrow(
        """
        select outbox.analysis_run_id, outbox.work_kind_code,
               run.knowledge_cutoff, run.idempotency_key,
               run.analysis_source_snapshot_id, snapshot.snapshot_sha256,
               scope.corporate_entity_id
        from analysis_run_outbox outbox
        join analysis_run run on run.analysis_run_id = outbox.analysis_run_id
        join analysis_run_scope scope on scope.analysis_run_id = run.analysis_run_id
        join analysis_source_snapshot snapshot
          on snapshot.analysis_source_snapshot_id = run.analysis_source_snapshot_id
        where outbox.analysis_run_id = $1
        for update of outbox
        """,
        analysis_run_id,
    )
    if outbox is None:
        raise AnalysisRunStartError(
            409,
            "Open this run. Start is only for a Pending lineage reconstruction "
            "or TEPP measurement.",
        )
    latest = await _latest_outbox_delivery(conn, analysis_run_id)
    if latest_outbox_delivery_is_delivered(latest):
        return await _visible_or_404(
            conn, analysis_run_id, account_id, affiliated_entity_ids
        )
    now = datetime.now(timezone.utc)
    try:
        if not latest_outbox_delivery_is_claimed(latest):
            await _append_outbox_delivery(
                conn,
                analysis_run_id,
                await _next_outbox_delivery_ordinal(conn, analysis_run_id),
                "analysis_outbox_claimed",
                now,
                valkey_stream_entry_id,
            )
        if outbox["work_kind_code"] == _TEPP_KIND:
            terminal = await _deliver_tepp_measurement(
                conn,
                analysis_run_id=analysis_run_id,
                locked=outbox,
                tepp_client=tepp_client or TeppClient(),
            )
        else:
            await _deliver_lineage_reconstruction(
                conn,
                analysis_run_id=analysis_run_id,
                locked=outbox,
                affiliated_entity_ids=affiliated_entity_ids,
                adjudication_client=adjudication_client,
            )
            terminal = True
        if terminal:
            finished = datetime.now(timezone.utc)
            if finished < now:
                finished = now
            await _append_outbox_delivery(
                conn,
                analysis_run_id,
                await _next_outbox_delivery_ordinal(conn, analysis_run_id),
                "analysis_outbox_delivered",
                finished,
                valkey_stream_entry_id,
            )
    except asyncpg.UniqueViolationError as exc:
        raise start_write_conflict_error() from exc
    return await _visible_or_404(
        conn, analysis_run_id, account_id, affiliated_entity_ids
    )


async def start_pending_analysis_run(
    conn: asyncpg.Connection,
    *,
    analysis_run_id: str,
    account_id: str,
    affiliated_entity_ids: list[str],
    tepp_client: TeppClient | None = None,
    adjudication_client: AdjudicationClient | None = None,
    valkey_stream_entry_id: str | None = None,
) -> dict[str, Any]:
    """Enqueue then deliver on one connection.

    The HTTP start path commits the outbox before this delivery so a
    crash leaves Running plus a durable work item. Callers that wrap
    both steps in one transaction keep the older all-or-nothing
    behavior.
    """
    queued = await enqueue_pending_analysis_run(
        conn,
        analysis_run_id=analysis_run_id,
        account_id=account_id,
        affiliated_entity_ids=affiliated_entity_ids,
    )
    if queued["status_code"] == _SUCCEEDED:
        return queued
    return await deliver_queued_analysis_run(
        conn,
        analysis_run_id=analysis_run_id,
        account_id=account_id,
        affiliated_entity_ids=affiliated_entity_ids,
        tepp_client=tepp_client,
        adjudication_client=adjudication_client,
        valkey_stream_entry_id=valkey_stream_entry_id,
    )


async def _deliver_lineage_reconstruction(
    conn: asyncpg.Connection,
    *,
    analysis_run_id: str,
    locked: asyncpg.Record,
    affiliated_entity_ids: list[str],
    adjudication_client: AdjudicationClient | None = None,
) -> None:
    """Persist ThreadWeave parent choices for the frozen bag."""
    now = datetime.now(timezone.utc)
    member_rows = await _snapshot_member_posts(
        conn,
        locked["analysis_source_snapshot_id"],
    )
    if member_rows:
        rows = member_rows
    else:
        rows = await _cutoff_source_posts(
            conn,
            corporate_entity_id=locked["corporate_entity_id"],
            knowledge_cutoff=locked["knowledge_cutoff"],
            affiliated_entity_ids=affiliated_entity_ids,
        )
    edges = lineage_edge_specs(records_from_source_posts(rows), llm=adjudication_client)
    digest = reconstruction_result_digest(edges)
    finished = datetime.now(timezone.utc)
    if finished < now:
        finished = now
    await conn.execute(
        """
        insert into analysis_run_reconstruction
            (analysis_run_id, result_sha256, edge_count, reconstructed_at, recorded_at)
        values ($1, $2, $3, clock_timestamp(), clock_timestamp())
        """,
        analysis_run_id,
        digest,
        len(edges),
    )
    for edge in edges:
        await conn.execute(
            """
            insert into analysis_run_lineage_edge
                (analysis_run_id, child_post_id, parent_post_id,
                 fused_score, reconstructed_at)
            values ($1, $2, $3, $4, $5)
            """,
            analysis_run_id,
            edge.child_id,
            edge.parent_id,
            edge.fused_score,
            finished,
        )
    await _append_status(
        conn,
        analysis_run_id,
        await _next_status_ordinal(conn, analysis_run_id),
        _SUCCEEDED,
    )


async def _deliver_tepp_measurement(
    conn: asyncpg.Connection,
    *,
    analysis_run_id: str,
    locked: asyncpg.Record,
    tepp_client: TeppClient,
) -> bool:
    """Submit the frozen snapshot through ``tepp_client``. Never persist a theta.

    Returns True when a terminal status was appended. An accepted
    receipt leaves the run Running and returns False so the outbox
    stays claimed until a completed result (TEPP#156) or a typed
    failure arrives.
    """
    request = tepp_run_request(
        idempotency_key=str(locked["idempotency_key"]),
        snapshot_sha256=str(locked["snapshot_sha256"]),
        knowledge_cutoff=locked["knowledge_cutoff"],
        corporate_entity_id=str(locked["corporate_entity_id"]),
    )
    receipt = await fetch_tepp_accepted_receipt(conn, analysis_run_id)
    outcome = (
        classify_tepp_status(tepp_client, request, str(receipt["remote_run_id"]))
        if receipt is not None
        else classify_tepp_submission(tepp_client, request)
    )
    if receipt is not None and outcome.status_code == _RUNNING:
        return False
    status_code = outcome.status_code
    failure_code = outcome.failure_code
    if outcome.persist_kind == _PERSIST_RESULT and outcome.envelope is not None:
        if not await _persist_tepp_result(
            conn,
            analysis_run_id=analysis_run_id,
            envelope=outcome.envelope,
        ):
            status_code = _FAILED
            failure_code = "tepp_result_not_persisted"
    elif outcome.persist_kind == _PERSIST_RECEIPT and outcome.envelope is not None:
        if await _persist_tepp_accepted_receipt(
            conn,
            analysis_run_id=analysis_run_id,
            envelope=outcome.envelope,
            request=request,
            knowledge_cutoff=locked["knowledge_cutoff"],
        ):
            return False
        status_code = _FAILED
        failure_code = "tepp_receipt_not_persisted"
    await _append_status(
        conn,
        analysis_run_id,
        await _next_status_ordinal(conn, analysis_run_id),
        status_code,
        failure_code or None,
    )
    return True
