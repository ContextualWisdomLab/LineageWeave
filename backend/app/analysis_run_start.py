"""Start a Pending lineage reconstruction or TEPP measurement.

ADR 0021 reconstructs lineage. ADR 0022 starts TEPP through
``tepp_client`` only. ADR 0023 enqueues that work on a durable outbox
so a crash after Running does not lose the item. ADR 0204 keeps provider
work outside database transactions and pool leases. Period-report stays
another path. Neither start invents a theta or a calibrated report
score.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

import asyncpg

from backend.app.analysis_run_ingestion import (
    AnalysisRunCreateError,
    fetch_visible_analysis_run,
)
from backend.app.post_eligibility import SOURCE_POST_ELIGIBILITY_SQL
from backend.app.analysis_run_outbox import (
    latest_outbox_delivery_is_claimed,
    latest_outbox_delivery_is_delivered,
    outbox_request_digest,
)
from backend.app.lineage_ingestion import (
    load_estimated_channel_weights,
    records_from_source_posts,
)
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
_TOPIC_LINEAGE_KIND = "analysis_run_topic_lineage"
_PENDING = "analysis_status_pending"
_RUNNING = "analysis_status_running"
_SUCCEEDED = "analysis_status_succeeded"
_FAILED = "analysis_status_failed"
_TEPP_MODEL_CONTRACT = "tepp-lineage-criterion-v1"
_TEPP_OUTPUT_PROFILE = "lineage_pair_criterion_anchor"
_TEPP_LINEAGE_ANCHOR_SCHEMA = "tepp.lineage_criterion_anchor.v1"
_TOPIC_LINEAGE_MODEL_CONTRACT = "tepp-topic-lineage-v1"
_TOPIC_LINEAGE_OUTPUT_PROFILE = "topic_identity_lineage"


class AnalysisRunStartError(AnalysisRunCreateError):
    """Fail-closed start: HTTP status plus a next-action detail string."""


class _AdjudicationProviderError(RuntimeError):
    """The adjudication provider (not our code) failed during a judge call."""


class _ProviderBoundaryAdjudication:
    """Convert judge-call provider failures into a typed boundary error.

    ``post_json`` raises ``HttpClientError``/``OSError`` on transport and
    HTTP failures and the content extraction raises
    ``ValueError``/``TypeError`` on malformed provider envelopes; those
    same builtin types raised by our reconstruction code would be real
    bugs, so the conversion happens only inside ``judge`` -- the one
    place a provider is actually on the line.
    """

    available = True

    def __init__(self, inner) -> None:
        self._inner = inner

    def judge(self, candidate_label: str, record_label: str) -> float:
        """Score one candidate pair, typing provider failures as such."""
        try:
            return self._inner.judge(candidate_label, record_label)
        except (HttpClientError, OSError, ValueError, TypeError) as exc:
            raise _AdjudicationProviderError(str(exc)) from exc


@dataclass(frozen=True)
class _DeliveryPlan:
    """Frozen provider input materialized by the short claim transaction."""

    work_kind_code: str
    started_at: datetime
    locked: dict[str, Any]
    records: tuple[Any, ...] = ()
    weights: dict[str, float] | None = None


@dataclass(frozen=True)
class _DeliveryOutcome:
    """Provider result ready for one short atomic persistence transaction."""

    work_kind_code: str
    started_at: datetime
    edges: tuple[Edge, ...] = ()
    status_code: str = _SUCCEEDED
    failure_code: str = ""
    envelope: dict[str, Any] | None = None
    source_snapshot_sha256: str | None = None
    knowledge_cutoff: datetime | None = None
    request: AnalysisRunRequest | None = None
    persist_receipt: bool = False
    persist_terminal_result: bool = False


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

    Lineage reconstructs the frozen bag. TEPP and topic-lineage submit
    through ``tepp_client`` and never invent a theta or a topic (ADR 0022 /
    ADR 0132). Period-report stays on its own rebuild path.
    """
    if run_kind_code in {_LINEAGE_KIND, _TEPP_KIND, _TOPIC_LINEAGE_KIND}:
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


def configured_tepp_client(transport_url: str = "", api_key: str = "") -> TeppClient:
    """Build a TEPP client from an optional HTTP transport URL.

    An empty URL keeps the default unavailable transport. A set URL
    POSTs TEPP's published wire payload. File URLs and other schemes
    stay unavailable -- this is not a local psychometric substitute.
    """
    url = transport_url.strip()
    if not url:
        return TeppClient()

    def transport(payload: dict[str, Any]) -> dict[str, Any]:
        """POST the TEPP wire payload to `url`, raising TeppNotAvailable on any transport failure."""
        try:
            headers = {
                "idempotency-key": str(payload["idempotency_key"]),
                "tepp-consumer": "lineageweave",
                "tepp-contract-version": str(payload["contract_version"]),
            }
            if api_key.strip():
                headers["authorization"] = f"Bearer {api_key}"
            return post_json(
                url,
                payload,
                headers=headers,
                timeout=30.0,
                service_peer_name="tepp",
            )
        except (HttpClientError, OSError, ValueError, TypeError) as exc:
            # Chain internally for operator logging; the exposed
            # message stays generic, never the raw provider exception text.
            raise TeppNotAvailable("TEPP transport unavailable") from exc

    return TeppClient(transport=transport)


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
        knowledge_cutoff=cutoff.astimezone(timezone.utc).isoformat().replace("+00:00", "Z"),
        model_contract_version=_TEPP_MODEL_CONTRACT,
        output_profile=_TEPP_OUTPUT_PROFILE,
    )


def topic_lineage_run_request(
    *,
    idempotency_key: str,
    snapshot_sha256: str,
    knowledge_cutoff: datetime,
    corporate_entity_id: str,
) -> AnalysisRunRequest:
    """Build TEPP's published request for a topic-lineage run (ADR 0132).

    Same wire shape as :func:`tepp_run_request` -- TEPP's
    ``AnalysisRunRequest`` already carries no post body or fabricated
    label -- only the model contract and output profile differ, selecting
    TRSL-TM topic identity plus CHRONOS/TDT event-intelligence status
    instead of calibrated psychometric measurement.
    """
    cutoff = knowledge_cutoff
    if cutoff.tzinfo is None:
        cutoff = cutoff.replace(tzinfo=timezone.utc)
    return AnalysisRunRequest(
        idempotency_key=idempotency_key,
        tenant_workspace_id=str(corporate_entity_id),
        snapshot_id=snapshot_sha256,
        knowledge_cutoff=cutoff.astimezone(timezone.utc).isoformat().replace("+00:00", "Z"),
        model_contract_version=_TOPIC_LINEAGE_MODEL_CONTRACT,
        output_profile=_TOPIC_LINEAGE_OUTPUT_PROFILE,
    )


def _tepp_submission(
    client: TeppClient,
    request: AnalysisRunRequest,
) -> tuple[str, str, dict[str, Any] | None]:
    """Submit through ``tepp_client`` and require a completed result envelope.

    TEPP's target HTTP contract is asynchronous. An ``accepted`` response is
    therefore not a measurement and remains ``tepp_result_not_persisted``.
    Only a provider-authoritative completed envelope can enter the database.
    """
    try:
        response = client.submit_analysis_run(request)
    except TeppNotAvailable:
        return _FAILED, "tepp_not_available", None
    except TeppInvalidResponse:
        return _FAILED, "tepp_result_not_persisted", None
    if not isinstance(response, dict):
        return _FAILED, "tepp_result_not_persisted", None
    state = response.get("status") or response.get("run_state")
    remote_run_id = response.get("analysis_run_id") or response.get("run_id")
    if state == "accepted":
        if (
            set(response)
            == {"contract_version", "run_id", "run_state", "idempotency_key"}
            and response["contract_version"] == 1
            and response["idempotency_key"] == request.idempotency_key
            and isinstance(remote_run_id, str)
            and remote_run_id.strip()
        ):
            return _RUNNING, "", response
        return _FAILED, "tepp_result_not_persisted", None
    if state not in {"completed", "succeeded"}:
        return _FAILED, "tepp_result_not_persisted", None
    if not isinstance(response.get("result"), dict):
        return _FAILED, "tepp_result_not_persisted", None
    if not isinstance(remote_run_id, str) or not remote_run_id.strip():
        return _FAILED, "tepp_result_not_persisted", None
    return _SUCCEEDED, "", response


def _tepp_status(
    client: TeppClient,
    request: AnalysisRunRequest,
    remote_run_id: str,
) -> tuple[str, str, dict[str, Any] | None]:
    """Read one strict provider status; unavailable reads remain retryable."""
    try:
        response = client.read_analysis_run_status(remote_run_id, request)
    except TeppNotAvailable:
        return _RUNNING, "", None
    except TeppInvalidResponse:
        return _FAILED, "tepp_result_not_persisted", None
    if response["run_state"] in {"accepted", "running"}:
        return _RUNNING, "", response
    terminal = response["terminal_result"]
    if response["run_state"] == "failed":
        return _FAILED, str(terminal["failure_code"]), response
    return _SUCCEEDED, "", response


async def _persist_tepp_terminal_result(
    conn: asyncpg.Connection,
    *,
    analysis_run_id: str,
    envelope: dict[str, Any],
) -> bool:
    """Persist a validated TEPP status envelope without reshaping its evidence."""
    remote_run_id = envelope.get("run_id")
    if envelope.get("run_state") != "succeeded" or not isinstance(remote_run_id, str):
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
                """,
                analysis_run_id,
                remote_run_id,
                result_json,
                result_sha256,
            )
    except (asyncpg.PostgresError, TypeError, ValueError):
        return False
    return True


async def _persist_tepp_receipt(
    conn: asyncpg.Connection,
    *,
    analysis_run_id: str,
    request: AnalysisRunRequest,
    envelope: dict[str, Any],
) -> bool:
    """Persist TEPP acceptance as transport evidence, never measurement."""
    remote_run_id = envelope.get("analysis_run_id") or envelope.get("run_id")
    state = envelope.get("status") or envelope.get("run_state")
    if not isinstance(remote_run_id, str) or state != "accepted":
        return False
    request_json = json.dumps(request.to_json(), separators=(",", ":"), sort_keys=True)
    receipt_json = json.dumps(envelope, separators=(",", ":"), sort_keys=True)
    request_sha256 = hashlib.sha256(request_json.encode()).hexdigest()
    receipt_sha256 = hashlib.sha256(receipt_json.encode()).hexdigest()
    try:
        async with conn.transaction():
            existing = await conn.fetchrow(
                """
                select remote_run_id, request_sha256, receipt_sha256
                from analysis_run_tepp_receipt
                where analysis_run_id = $1
                """,
                analysis_run_id,
            )
            if existing is not None:
                return (
                    str(existing["remote_run_id"]) == remote_run_id
                    and str(existing["request_sha256"]) == request_sha256
                    and str(existing["receipt_sha256"]) == receipt_sha256
                )
            await conn.execute(
                """
                insert into analysis_run_tepp_receipt
                    (analysis_run_id, remote_run_id, request_sha256, receipt_sha256,
                     accepted_status_code)
                values ($1, $2, $3, $4, $5)
                """,
                analysis_run_id,
                remote_run_id,
                request_sha256,
                receipt_sha256,
                state,
            )
    except (asyncpg.PostgresError, TypeError, ValueError):
        return False
    return True


def tepp_submit_outcome(
    client: TeppClient,
    request: AnalysisRunRequest,
) -> tuple[str, str]:
    """Compatibility projection of the TEPP submission outcome."""
    status_code, failure_code, _ = _tepp_submission(client, request)
    return status_code, failure_code


def _topic_lineage_envelope_is_valid(envelope: dict[str, Any]) -> bool:
    """Require TEPP's versioned topic-identity/CHRONOS-status contract (ADR 0132).

    ``_tepp_submission`` only checks that ``result`` is *a* dict -- a
    ``completed`` envelope carrying the calibrated-measurement shape (or any
    other unrelated payload) would pass it too, since both requests share the
    same wire contract and differ only in ``model_contract_version`` /
    ``output_profile``. This additionally requires TRSL-TM topic identity and
    CHRONOS/TDT status, keyed by envelope version.
    """
    result = envelope.get("result")
    if not isinstance(result, dict):
        return False
    if type(result.get("envelope_version")) is not int:  # bool is not a version
        return False
    if result["envelope_version"] != 1:
        return False
    topic_identity = result.get("topic_identity")
    if not isinstance(topic_identity, (list, dict)) or not topic_identity:
        return False
    chronos_status = result.get("chronos_status")
    if not isinstance(chronos_status, (list, dict, str)) or not chronos_status:
        return False
    return True


def topic_lineage_submit_outcome(
    client: TeppClient,
    request: AnalysisRunRequest,
) -> tuple[str, str, dict[str, Any] | None]:
    """Submit through ``tepp_client`` and require the topic-lineage contract.

    Mirrors :func:`tepp_submit_outcome`, but a syntactically ``completed``
    envelope that omits the versioned topic-identity/CHRONOS-status contract
    is also Failed (``tepp_topic_contract_unavailable``, ADR 0132 Decision
    item 3), not silently persisted as a topic-lineage result.
    """
    status_code, failure_code, envelope = _tepp_submission(client, request)
    if status_code == _RUNNING:
        return _FAILED, "tepp_result_not_persisted", None
    if status_code == _SUCCEEDED and not (
        envelope is not None and _topic_lineage_envelope_is_valid(envelope)
    ):
        return _FAILED, "tepp_topic_contract_unavailable", None
    return status_code, failure_code, envelope


async def _persist_tepp_result(
    conn: asyncpg.Connection,
    *,
    analysis_run_id: str,
    envelope: dict[str, Any],
    expected_snapshot_sha256: str,
    expected_knowledge_cutoff: datetime,
) -> bool:
    """Persist a completed TEPP envelope and any exact lineage anchor projection."""
    remote_run_id = envelope.get("analysis_run_id") or envelope.get("run_id")
    if not isinstance(remote_run_id, str) or not remote_run_id.strip():
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
            anchor = envelope.get("result")
            if (
                envelope.get("result_schema_version") == _TEPP_LINEAGE_ANCHOR_SCHEMA
                and isinstance(anchor, dict)
            ):
                try:
                    raw_estimation_run_id = str(anchor["estimation_run_id"])
                    estimation_run_id = str(UUID(raw_estimation_run_id))
                    anchor_cutoff = datetime.fromisoformat(
                        str(anchor["knowledge_cutoff"]).replace("Z", "+00:00")
                    )
                except (KeyError, TypeError, ValueError):
                    anchor = None
                expected_cutoff = expected_knowledge_cutoff
                if expected_cutoff.tzinfo is None:
                    expected_cutoff = expected_cutoff.replace(tzinfo=timezone.utc)
                if anchor is not None and (
                    anchor.get("anchor_kind_code") != "lineage_pair_criterion"
                    or anchor.get("contract_version") != 1
                    or raw_estimation_run_id != estimation_run_id
                    or anchor.get("source_snapshot_sha256") != expected_snapshot_sha256
                    or anchor_cutoff != expected_cutoff
                    or anchor.get("criterion_validity_status") != "accepted"
                    or type(anchor.get("validated_pair_count")) is not int
                    or anchor["validated_pair_count"] <= 0
                ):
                    anchor = None
                if anchor is not None:
                    await conn.execute(
                        """
                        insert into lineage_weight_tepp_anchor
                            (estimation_run_id, tepp_analysis_run_id,
                             anchor_kind_code, anchor_contract_version,
                             source_snapshot_sha256, knowledge_cutoff,
                             criterion_validity_status_code, validated_pair_count)
                        values ($1, $2, $3, $4, $5, $6, $7, $8)
                        on conflict (estimation_run_id) do nothing
                        """,
                        estimation_run_id,
                        analysis_run_id,
                        anchor["anchor_kind_code"],
                        anchor["contract_version"],
                        anchor["source_snapshot_sha256"],
                        anchor_cutoff,
                        anchor["criterion_validity_status"],
                        anchor["validated_pair_count"],
                    )
                    await conn.execute(
                        """
                        update lineage_channel_weight
                           set anchor_method_code = 'tepp_lineage_criterion_v1'
                         where estimation_run_id = $1
                           and estimation_method_code = 'mls2plm_expected_information'
                           and source_snapshot_sha256 = $2
                           and knowledge_cutoff = $3
                           and sample_pair_count = $4
                        """,
                        estimation_run_id,
                        anchor["source_snapshot_sha256"],
                        anchor_cutoff,
                        anchor["validated_pair_count"],
                    )
    except (asyncpg.PostgresError, TypeError, ValueError):
        return False
    return True


async def _persist_topic_lineage_result(
    conn: asyncpg.Connection,
    *,
    analysis_run_id: str,
    envelope: dict[str, Any],
) -> bool:
    """Persist only a validated, remote-completed topic-lineage envelope.

    Stores TEPP's TRSL-TM topic identity / CHRONOS status envelope
    verbatim (ADR 0132); LineageWeave does not decompose or reinterpret
    its evidence/inference/prediction fields here.
    """
    remote_run_id = envelope.get("analysis_run_id") or envelope.get("run_id")
    if not isinstance(remote_run_id, str) or not remote_run_id.strip():
        return False
    result_json = json.dumps(envelope, separators=(",", ":"), sort_keys=True)
    result_sha256 = hashlib.sha256(result_json.encode("utf-8")).hexdigest()
    try:
        async with conn.transaction():
            await conn.execute(
                """
                insert into analysis_run_topic_lineage_result
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
    occurred_at: datetime,
    failure_code: str | None = None,
) -> None:
    """Append one legal lifecycle event. Failed rows carry a machine code."""
    await conn.execute(
        """
        insert into analysis_run_status_event
            (analysis_run_id, status_ordinal, status_code, occurred_at, failure_code)
        values ($1, $2, $3, clock_timestamp(), $4)
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
            now,
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
    pool: asyncpg.Pool,
    *,
    database_url: str,
    analysis_run_id: str,
    account_id: str,
    affiliated_entity_ids: list[str],
    tepp_client: TeppClient | None = None,
    adjudication_client: AdjudicationClient | None = None,
    valkey_stream_entry_id: str | None = None,
) -> dict[str, Any]:
    """Claim, compute without a pool slot, then atomically persist delivery.

    A delivered row replays the stored result. Missing work is 409.
    TEPP stays Failed when the transport is missing or the envelope is
    not persistable. A dedicated PostgreSQL session owns the run-level
    advisory lock; it carries no transaction and is not a pool slot.
    """
    try:
        UUID(analysis_run_id)
    except ValueError as exc:
        raise AnalysisRunStartError(404, "This analysis run is not visible.") from exc

    lock_conn = await asyncpg.connect(database_url)
    try:
        acquired = await lock_conn.fetchval(
            "select pg_try_advisory_lock("
            "hashtextextended('lineageweave:analysis-run:' || $1, 0))",
            analysis_run_id,
        )
        if not acquired:
            async with pool.acquire() as conn:
                current = await _visible_or_404(
                    conn, analysis_run_id, account_id, affiliated_entity_ids
                )
            if current["status_code"] == _SUCCEEDED:
                return current
            raise AnalysisRunStartError(
                409,
                "Open this run. Delivery is already running; refresh to read its result.",
            )

        async with pool.acquire() as conn:
            async with conn.transaction():
                plan_or_result = await _claim_delivery_plan(
                    conn,
                    analysis_run_id=analysis_run_id,
                    account_id=account_id,
                    affiliated_entity_ids=affiliated_entity_ids,
                    adjudication_client=adjudication_client,
                    valkey_stream_entry_id=valkey_stream_entry_id,
                )
        if isinstance(plan_or_result, dict):
            return plan_or_result

        outcome = await asyncio.to_thread(
            _execute_delivery_plan,
            plan_or_result,
            tepp_client or TeppClient(),
            adjudication_client,
        )
        async with pool.acquire() as conn:
            async with conn.transaction():
                return await _persist_delivery_outcome(
                    conn,
                    analysis_run_id=analysis_run_id,
                    account_id=account_id,
                    affiliated_entity_ids=affiliated_entity_ids,
                    outcome=outcome,
                    valkey_stream_entry_id=valkey_stream_entry_id,
                )
    finally:
        await lock_conn.close()


async def _claim_delivery_plan(
    conn: asyncpg.Connection,
    *,
    analysis_run_id: str,
    account_id: str,
    affiliated_entity_ids: list[str],
    adjudication_client: AdjudicationClient | None,
    valkey_stream_entry_id: str | None,
) -> _DeliveryPlan | dict[str, Any]:
    """Commit the claim and materialize immutable provider input."""
    current = await fetch_visible_analysis_run(
        conn, analysis_run_id, account_id, affiliated_entity_ids
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
               scope.corporate_entity_id, receipt.remote_run_id
        from analysis_run_outbox outbox
        join analysis_run run on run.analysis_run_id = outbox.analysis_run_id
        join analysis_run_scope scope on scope.analysis_run_id = run.analysis_run_id
        join analysis_source_snapshot snapshot
          on snapshot.analysis_source_snapshot_id = run.analysis_source_snapshot_id
        left join analysis_run_tepp_receipt receipt
          on receipt.analysis_run_id = run.analysis_run_id
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
    started_at = datetime.now(timezone.utc)
    if not latest_outbox_delivery_is_claimed(latest):
        try:
            await _append_outbox_delivery(
                conn,
                analysis_run_id,
                await _next_outbox_delivery_ordinal(conn, analysis_run_id),
                "analysis_outbox_claimed",
                started_at,
                valkey_stream_entry_id,
            )
        except asyncpg.UniqueViolationError as exc:
            raise start_write_conflict_error() from exc
    locked = dict(outbox)
    if outbox["work_kind_code"] != _LINEAGE_KIND:
        return _DeliveryPlan(str(outbox["work_kind_code"]), started_at, locked)

    member_rows = await _snapshot_member_posts(
        conn, outbox["analysis_source_snapshot_id"]
    )
    rows = member_rows or await _cutoff_source_posts(
        conn,
        corporate_entity_id=outbox["corporate_entity_id"],
        knowledge_cutoff=outbox["knowledge_cutoff"],
        affiliated_entity_ids=affiliated_entity_ids,
    )
    active_channels = {"temporal", "secondary_key", "text"}
    if adjudication_client is not None and getattr(adjudication_client, "available", False):
        active_channels.add("llm")
    weights = await load_estimated_channel_weights(conn, active_channels)
    if weights is None:
        raise AnalysisRunStartError(
            503,
            "Channel weights are not estimated yet for this run's active "
            f"channels ({', '.join(sorted(active_channels))}). Run "
            "scripts/estimate_channel_weights.py, then start this run again.",
        )
    return _DeliveryPlan(
        _LINEAGE_KIND,
        started_at,
        locked,
        tuple(records_from_source_posts(rows)),
        dict(weights),
    )


def _execute_delivery_plan(
    plan: _DeliveryPlan,
    tepp_client: TeppClient,
    adjudication_client: AdjudicationClient | None,
) -> _DeliveryOutcome:
    """Run provider or reconstruction work with no database resource."""
    if plan.work_kind_code == _LINEAGE_KIND:
        guarded_client = (
            _ProviderBoundaryAdjudication(adjudication_client)
            if plan.weights is not None and "llm" in plan.weights
            else adjudication_client
        )
        try:
            edges = lineage_edge_specs(
                list(plan.records), llm=guarded_client, weights=plan.weights or {}
            )
        except _AdjudicationProviderError as exc:
            raise AnalysisRunStartError(
                503,
                "The adjudication provider failed mid-reconstruction; nothing "
                "was persisted. Check the contextual-orchestrator transport, "
                "then start this run again.",
            ) from exc
        return _DeliveryOutcome(plan.work_kind_code, plan.started_at, tuple(edges))

    request_factory = (
        topic_lineage_run_request
        if plan.work_kind_code == _TOPIC_LINEAGE_KIND
        else tepp_run_request
    )
    request = request_factory(
        idempotency_key=str(plan.locked["idempotency_key"]),
        snapshot_sha256=str(plan.locked["snapshot_sha256"]),
        knowledge_cutoff=plan.locked["knowledge_cutoff"],
        corporate_entity_id=str(plan.locked["corporate_entity_id"]),
    )
    persist_receipt = False
    persist_terminal_result = False
    if plan.work_kind_code == _TOPIC_LINEAGE_KIND:
        status_code, failure_code, envelope = topic_lineage_submit_outcome(
            tepp_client, request
        )
    elif plan.locked.get("remote_run_id"):
        status_code, failure_code, envelope = _tepp_status(
            tepp_client, request, str(plan.locked["remote_run_id"])
        )
        persist_terminal_result = status_code == _SUCCEEDED and envelope is not None
    else:
        status_code, failure_code, envelope = _tepp_submission(tepp_client, request)
        persist_receipt = status_code == _RUNNING and envelope is not None
    return _DeliveryOutcome(
        plan.work_kind_code,
        plan.started_at,
        status_code=status_code,
        failure_code=failure_code,
        envelope=envelope,
        source_snapshot_sha256=str(plan.locked["snapshot_sha256"]),
        knowledge_cutoff=plan.locked["knowledge_cutoff"],
        request=request,
        persist_receipt=persist_receipt,
        persist_terminal_result=persist_terminal_result,
    )


async def _persist_delivery_outcome(
    conn: asyncpg.Connection,
    *,
    analysis_run_id: str,
    account_id: str,
    affiliated_entity_ids: list[str],
    outcome: _DeliveryOutcome,
    valkey_stream_entry_id: str | None,
) -> dict[str, Any]:
    """Persist one complete outcome and delivered event atomically."""
    outbox = await conn.fetchrow(
        "select analysis_run_id from analysis_run_outbox where analysis_run_id = $1 for update",
        analysis_run_id,
    )
    if outbox is None:
        raise AnalysisRunStartError(409, "Open this run. Its queued work no longer exists.")
    latest = await _latest_outbox_delivery(conn, analysis_run_id)
    if latest_outbox_delivery_is_delivered(latest):
        return await _visible_or_404(
            conn, analysis_run_id, account_id, affiliated_entity_ids
        )
    finished = max(datetime.now(timezone.utc), outcome.started_at)
    status_code = outcome.status_code
    failure_code = outcome.failure_code
    if outcome.work_kind_code == _TEPP_KIND and outcome.status_code == _RUNNING:
        if outcome.persist_receipt:
            persisted_receipt = (
                outcome.envelope is not None
                and outcome.request is not None
                and await _persist_tepp_receipt(
                    conn,
                    analysis_run_id=analysis_run_id,
                    request=outcome.request,
                    envelope=outcome.envelope,
                )
            )
            if not persisted_receipt:
                status_code = _FAILED
                failure_code = "tepp_receipt_not_persisted"
            else:
                return await _visible_or_404(
                    conn, analysis_run_id, account_id, affiliated_entity_ids
                )
        else:
            return await _visible_or_404(
                conn, analysis_run_id, account_id, affiliated_entity_ids
            )
    if outcome.work_kind_code == _LINEAGE_KIND:
        await _persist_lineage_reconstruction(
            conn, analysis_run_id=analysis_run_id, edges=outcome.edges, finished=finished
        )
    elif outcome.status_code == _SUCCEEDED and outcome.envelope is not None:
        if outcome.persist_terminal_result:
            persisted = await _persist_tepp_terminal_result(
                conn,
                analysis_run_id=analysis_run_id,
                envelope=outcome.envelope,
            )
        elif outcome.work_kind_code == _TOPIC_LINEAGE_KIND:
            persisted = await _persist_topic_lineage_result(
                conn, analysis_run_id=analysis_run_id, envelope=outcome.envelope
            )
        elif (
            outcome.source_snapshot_sha256 is not None
            and outcome.knowledge_cutoff is not None
        ):
            persisted = await _persist_tepp_result(
                conn,
                analysis_run_id=analysis_run_id,
                envelope=outcome.envelope,
                expected_snapshot_sha256=outcome.source_snapshot_sha256,
                expected_knowledge_cutoff=outcome.knowledge_cutoff,
            )
        else:
            persisted = False
        if not persisted:
            status_code = _FAILED
            failure_code = "tepp_result_not_persisted"
    if outcome.work_kind_code != _LINEAGE_KIND:
        await _append_status(
            conn,
            analysis_run_id,
            await _next_status_ordinal(conn, analysis_run_id),
            status_code,
            finished,
            failure_code,
        )
    await _append_outbox_delivery(
        conn,
        analysis_run_id,
        await _next_outbox_delivery_ordinal(conn, analysis_run_id),
        "analysis_outbox_delivered",
        finished,
        valkey_stream_entry_id,
    )
    return await _visible_or_404(
        conn, analysis_run_id, account_id, affiliated_entity_ids
    )


async def _persist_lineage_reconstruction(
    conn: asyncpg.Connection,
    *,
    analysis_run_id: str,
    edges: tuple[Edge, ...],
    finished: datetime,
) -> None:
    """Persist complete ThreadWeave parent choices in the completion transaction."""
    digest = reconstruction_result_digest(edges)
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
        finished,
    )
