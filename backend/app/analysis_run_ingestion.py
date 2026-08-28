"""Authorized, source-redacting reads of the Milestone 2 analysis-run registry.

The registry itself is issue #89 / migration 0018. This module is the
product projection: an account sees only runs they requested or whose
scope they already have ABAC authority to walk. Aggregate counts and
lookup labels come back; source SQL, DSNs, raw records, and provider
payloads never do.

``create_pending_analysis_run`` (ADR 0017) writes snapshot, counts, frozen
membership, run, scope, and the first Pending event atomically. It
records lineage only. It does not reconstruct lineage, accept a TEPP
kind, or invent a score. ``enqueue_pending_analysis_run`` then
``deliver_queued_analysis_run`` later reconstruct lineage (ADR 0021 /
ADR 0023) or submit TEPP through ``tepp_client`` (ADR 0022). Neither
path invents a TEPP score.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

import asyncpg

from backend.app.demo_scope import has_real_source_context, is_demo_scope
from backend.app.knowledge_graph import labels_for_codes
from backend.app.post_eligibility import SOURCE_POST_ELIGIBILITY_SQL
from lineageweave import __version__ as PACKAGE_VERSION

_LINEAGE_RUN_KIND = "analysis_run_lineage"
_TEPP_RUN_KIND = "analysis_run_tepp"
_REPORT_RUN_KIND = "analysis_run_report"
_TOPIC_LINEAGE_RUN_KIND = "analysis_run_topic_lineage"
_CORPORATE_SCOPE = "analysis_scope_corporate_entity"
_CAPTURE_CONTRACT_VERSION = "analysis-run-capture-v1"
_KIND_SCHEMA_VERSION = {
    "analysis_run_lineage": "lineage-run-v1",
    "analysis_run_tepp": "tepp-run-v1",
    "analysis_run_topic_lineage": "topic-lineage-run-v1",
}

_RUN_LIST_SQL = f"""
    select
      run.analysis_run_id,
      run.run_kind_code,
      run.knowledge_cutoff,
      run.requested_at,
      run.configuration_schema_version,
      run.configuration_sha256,
      run.code_revision_sha,
      scope.scope_kind_code,
      scope.corporate_entity_id,
      scope.process_unit_id,
      scope.scope_key,
      corp.entity_name as scope_entity_name,
      corp.corporate_entity_code as scope_entity_code,
      status.status_code,
      status.failure_code
    from analysis_run run
    join analysis_run_scope scope on scope.analysis_run_id = run.analysis_run_id
    left join analysis_run_current_status status
      on status.analysis_run_id = run.analysis_run_id
    left join corporate_entity corp
      on corp.corporate_entity_id = scope.corporate_entity_id
    where
      run.requested_by_account_id = $1
      or (
        scope.scope_kind_code = 'analysis_scope_corporate_entity'
        and scope.corporate_entity_id = any($2::uuid[])
      )
      or (
        scope.scope_kind_code = 'analysis_scope_process_unit'
        and exists (
          select 1 from account_affiliation aff
          where aff.user_account_id = $1
            and aff.process_unit_id = scope.process_unit_id
        )
      )
      or (
        scope.scope_kind_code = 'analysis_scope_thread_group'
        and exists (
          select 1 from source_post p
          where p.thread_group_key = scope.scope_key
            and p.created_at <= run.knowledge_cutoff
            and {SOURCE_POST_ELIGIBILITY_SQL.format(alias="p")}
            and (
              p.visibility_code = 'public'
              or p.corporate_entity_id = any($2::uuid[])
            )
        )
      )
    order by run.requested_at desc
"""

_RUN_DETAIL_SQL = f"""
    select
      run.analysis_run_id,
      run.run_kind_code,
      run.knowledge_cutoff,
      run.requested_at,
      run.configuration_schema_version,
      run.configuration_sha256,
      run.code_revision_sha,
      scope.scope_kind_code,
      scope.corporate_entity_id,
      scope.process_unit_id,
      scope.scope_key,
      corp.entity_name as scope_entity_name,
      status.status_code,
      status.failure_code
    from analysis_run run
    join analysis_run_scope scope on scope.analysis_run_id = run.analysis_run_id
    left join analysis_run_current_status status
      on status.analysis_run_id = run.analysis_run_id
    left join corporate_entity corp
      on corp.corporate_entity_id = scope.corporate_entity_id
    where run.analysis_run_id = $3
      and (
        run.requested_by_account_id = $1
        or (
          scope.scope_kind_code = 'analysis_scope_corporate_entity'
          and scope.corporate_entity_id = any($2::uuid[])
        )
        or (
          scope.scope_kind_code = 'analysis_scope_process_unit'
          and exists (
            select 1 from account_affiliation aff
            where aff.user_account_id = $1
              and aff.process_unit_id = scope.process_unit_id
          )
        )
        or (
          scope.scope_kind_code = 'analysis_scope_thread_group'
          and exists (
            select 1 from source_post p
          where p.thread_group_key = scope.scope_key
            and p.created_at <= run.knowledge_cutoff
            and {SOURCE_POST_ELIGIBILITY_SQL.format(alias="p")}
            and (
                p.visibility_code = 'public'
                or p.corporate_entity_id = any($2::uuid[])
              )
          )
        )
      )
    order by run.requested_at desc
"""

_COUNTS_BY_RUN_SQL = """
    select run.analysis_run_id, counts.count_type_code, counts.count_value
    from analysis_run run
    join analysis_source_count counts
      on counts.analysis_source_snapshot_id = run.analysis_source_snapshot_id
    where run.analysis_run_id = any($1::uuid[])
    order by counts.count_type_code
"""


def scope_grouping_key(row: Any) -> str | None:
    """Persist the reconstruct grouping key for the run's authorized scope.

    A corporate-entity report run stores the week on ``scope_key``. The
    grouping that reconstruct and the period-report panel share is the
    corporate entity (or process unit / thread group), never that week
    label and never a theta.
    """
    scope = row["scope_kind_code"]
    if scope == "analysis_scope_corporate_entity" and row["corporate_entity_id"]:
        return str(row["corporate_entity_id"])
    if scope == "analysis_scope_process_unit" and row["process_unit_id"]:
        return str(row["process_unit_id"])
    if scope == "analysis_scope_thread_group" and row["scope_key"]:
        return str(row["scope_key"])
    return None


def _iso(value: Any) -> str:
    """Serialize a timestamptz the same way post payloads do."""
    return value.isoformat() if hasattr(value, "isoformat") else str(value)


def _as_utc(value: datetime) -> datetime:
    """Treat a naive clock as UTC so cutoff comparison stays timezone-aware."""
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def live_write_after_cutoff(updated_at: datetime, knowledge_cutoff: datetime) -> bool:
    """True when the live row was rewritten after the run's analysis clock.

    ``created_at <= knowledge_cutoff`` admits the title. ``updated_at`` is
    the live write clock (ADR 0016). Equal times stay in-cutoff evidence.
    """
    return _as_utc(updated_at) > _as_utc(knowledge_cutoff)


async def _counts_by_run(
    conn: asyncpg.Connection,
    run_ids: list[str],
) -> dict[str, list[asyncpg.Record]]:
    """Load aggregate snapshot counts for the given runs."""
    if not run_ids:
        return {}
    # Safe SQL: this immutable aggregate query has closed schema text; run ids remain bound below.
    rows = await conn.fetch(  # nosemgrep: python.lang.security.audit.sqli.asyncpg-sqli.asyncpg-sqli
        _COUNTS_BY_RUN_SQL,
        run_ids,
    )
    grouped: dict[str, list[asyncpg.Record]] = {}
    for row in rows:
        grouped.setdefault(str(row["analysis_run_id"]), []).append(row)
    return grouped


async def _status_history(
    conn: asyncpg.Connection,
    analysis_run_id: str,
) -> list[dict[str, Any]]:
    """Labeled append-only lifecycle for one already-visible run."""
    rows = await conn.fetch(
        """
        select status_ordinal, status_code, occurred_at, failure_code
        from analysis_run_status_event
        where analysis_run_id = $1::uuid
        order by status_ordinal
        """,
        analysis_run_id,
    )
    labels = await labels_for_codes(conn, [row["status_code"] for row in rows])
    history: list[dict[str, Any]] = []
    for row in rows:
        item: dict[str, Any] = {
            "status_ordinal": int(row["status_ordinal"]),
            "status_code": row["status_code"],
            "status_label": labels.get(row["status_code"], row["status_code"]),
            "occurred_at": _iso(row["occurred_at"]),
        }
        if row["failure_code"]:
            item["failure_code"] = row["failure_code"]
        history.append(item)
    return history


async def fetch_outbox_deliveries(
    conn: asyncpg.Connection,
    analysis_run_id: str,
) -> list[dict[str, Any]]:
    """Labeled claim/delivery events for one already-visible run.

    Missing outbox tables mean migration 0023 is not applied. Stream
    entry ids stay off the payload -- they are not buyer evidence.
    """
    try:
        rows = await conn.fetch(
            """
            select delivery_ordinal, delivery_status_code, occurred_at
            from analysis_run_outbox_delivery
            where analysis_run_id = $1::uuid
            order by delivery_ordinal
            """,
            analysis_run_id,
        )
    except asyncpg.UndefinedTableError:
        return []
    labels = await labels_for_codes(
        conn,
        [row["delivery_status_code"] for row in rows],
    )
    return [
        {
            "delivery_ordinal": int(row["delivery_ordinal"]),
            "delivery_status_code": row["delivery_status_code"],
            "delivery_status_label": labels.get(
                row["delivery_status_code"],
                row["delivery_status_code"],
            ),
            "occurred_at": _iso(row["occurred_at"]),
        }
        for row in rows
    ]


async def _serialize_runs(
    conn: asyncpg.Connection,
    rows: list[asyncpg.Record],
) -> list[dict[str, Any]]:
    """Project registry rows into the authorized buyer-facing payload."""
    if not rows:
        return []
    count_rows = await _counts_by_run(conn, [str(row["analysis_run_id"]) for row in rows])
    labels = await labels_for_codes(
        conn,
        [row["run_kind_code"] for row in rows]
        + [row["scope_kind_code"] for row in rows]
        + [row["status_code"] for row in rows if row["status_code"]]
        + [
            count["count_type_code"]
            for counts in count_rows.values()
            for count in counts
        ],
    )
    payload: list[dict[str, Any]] = []
    for row in rows:
        run_id = str(row["analysis_run_id"])
        kind = row["run_kind_code"]
        scope = row["scope_kind_code"]
        status = row["status_code"]
        item: dict[str, Any] = {
            "analysis_run_id": run_id,
            "run_kind_code": kind,
            "run_kind_label": labels.get(kind, kind),
            "scope_kind_code": scope,
            "scope_kind_label": labels.get(scope, scope),
            "status_code": status,
            "status_label": labels.get(status, status) if status else None,
            "knowledge_cutoff": _iso(row["knowledge_cutoff"]),
            "requested_at": _iso(row["requested_at"]),
            "source_counts": [
                {
                    "count_type_code": count["count_type_code"],
                    "count_type_label": labels.get(
                        count["count_type_code"], count["count_type_code"]
                    ),
                    "count_value": int(count["count_value"]),
                }
                for count in count_rows.get(run_id, [])
            ],
        }
        if row["scope_entity_name"]:
            item["scope_entity_name"] = row["scope_entity_name"]
        if row["scope_key"]:
            item["scope_key"] = row["scope_key"]
        grouping_key = scope_grouping_key(row)
        if grouping_key:
            item["scope_grouping_key"] = grouping_key
        payload.append(item)
    return payload


async def fetch_visible_analysis_runs(
    conn: asyncpg.Connection,
    account_id: str,
    affiliated_entity_ids: list[str],
) -> list[dict[str, Any]]:
    """Runs the account requested or whose scope they may already walk.

    Once real source-import evidence is visible, the synthetic `make seed`
    Demo Corp runs stop appearing here -- a buyer must not mistake that
    fabricated narrative for real evidence (ADR 0001 / ADR 0042).
    """
    # Safe SQL: this immutable module query contains only closed schema SQL; request values remain bound below.
    rows = await conn.fetch(  # nosemgrep: python.lang.security.audit.sqli.asyncpg-sqli.asyncpg-sqli
        _RUN_LIST_SQL,
        account_id,
        affiliated_entity_ids,
    )
    if rows and await has_real_source_context(conn, affiliated_entity_ids):
        rows = [row for row in rows if not is_demo_scope(row["scope_entity_code"])]
    return await _serialize_runs(conn, rows)


async def fetch_visible_analysis_run(
    conn: asyncpg.Connection,
    analysis_run_id: str,
    account_id: str,
    affiliated_entity_ids: list[str],
) -> dict[str, Any] | None:
    """One visible run, or None when it is missing or hidden."""
    # Safe SQL: this immutable module query contains only closed schema SQL; request values remain bound below.
    rows = await conn.fetch(  # nosemgrep: python.lang.security.audit.sqli.asyncpg-sqli.asyncpg-sqli
        _RUN_DETAIL_SQL,
        account_id,
        affiliated_entity_ids,
        analysis_run_id,
    )
    payload = await _serialize_runs(conn, rows)
    if not payload:
        return None
    detail = payload[0]
    row = rows[0]
    detail["configuration_schema_version"] = row["configuration_schema_version"]
    detail["configuration_sha256"] = row["configuration_sha256"]
    detail["code_revision_sha"] = row["code_revision_sha"]
    if row["failure_code"]:
        detail["failure_code"] = row["failure_code"]
    detail["status_history"] = await _status_history(conn, analysis_run_id)
    detail["outbox_deliveries"] = await fetch_outbox_deliveries(conn, analysis_run_id)
    detail["visible_posts"] = await fetch_visible_scope_posts(
        conn,
        row["scope_kind_code"],
        row["corporate_entity_id"],
        row["process_unit_id"],
        row["scope_key"],
        affiliated_entity_ids,
        row["knowledge_cutoff"],
    )
    digest, edges = await fetch_reconstructed_edges(
        conn,
        analysis_run_id,
        affiliated_entity_ids,
    )
    if digest is not None:
        detail["reconstruction_result_sha256"] = digest
    detail["reconstructed_edges"] = edges
    if row["run_kind_code"] == _TOPIC_LINEAGE_RUN_KIND:
        topic_result = await conn.fetchrow(
            """
            select result_json, result_sha256
              from analysis_run_topic_lineage_result
             where analysis_run_id = $1
            """,
            analysis_run_id,
        )
        if topic_result is not None:
            envelope = topic_result["result_json"]
            detail["topic_lineage_result"] = (
                json.loads(envelope) if isinstance(envelope, str) else envelope
            )
            detail["topic_lineage_result_sha256"] = topic_result["result_sha256"]
    if row["run_kind_code"] == _TEPP_RUN_KIND:
        receipt = await conn.fetchrow(
            """
            select remote_run_id, accepted_status_code, received_at
            from analysis_run_tepp_receipt
            where analysis_run_id = $1
            """,
            analysis_run_id,
        )
        if receipt is not None:
            detail["tepp_accepted_receipt"] = {
                "remote_run_id": str(receipt["remote_run_id"]),
                "accepted_status_code": str(receipt["accepted_status_code"]),
                "received_at": _iso(receipt["received_at"]),
            }
    return detail


def reconstructed_edge_is_visible(
    *,
    parent_visibility_code: str,
    parent_corporate_entity_id: Any,
    child_visibility_code: str,
    child_corporate_entity_id: Any,
    affiliated_entity_ids: list[str],
) -> bool:
    """Hide an edge when either endpoint is outside the caller's ABAC bag."""
    affiliated = {str(entity_id) for entity_id in affiliated_entity_ids}
    parent_visible = (
        parent_visibility_code == "public"
        or str(parent_corporate_entity_id) in affiliated
    )
    child_visible = (
        child_visibility_code == "public"
        or str(child_corporate_entity_id) in affiliated
    )
    return parent_visible and child_visible


async def fetch_reconstructed_edges(
    conn: asyncpg.Connection,
    analysis_run_id: str,
    affiliated_entity_ids: list[str],
) -> tuple[str | None, list[dict[str, Any]]]:
    """Return the persisted digest and titled edges, or ``(None, [])``.

    Missing reconstruction tables mean this database has not applied
    migration 0021 yet; treat that as no stored tree rather than 500.
    Titles follow the same public-or-affiliated rule as ``visible_posts``.
    """
    try:
        header = await conn.fetchrow(
            """
            select result_sha256
            from analysis_run_reconstruction
            where analysis_run_id = $1
            """,
            analysis_run_id,
        )
    except asyncpg.UndefinedTableError:
        return None, []
    if header is None:
        return None, []
    # Safe SQL: eligibility fragments are immutable schema predicates; the run id remains a bound parameter.
    rows = await conn.fetch(  # nosemgrep: python.lang.security.audit.sqli.asyncpg-sqli.asyncpg-sqli
        f"""
        select
          edge.parent_post_id,
          parent_post.post_title as parent_post_title,
          parent_post.visibility_code as parent_visibility_code,
          parent_post.corporate_entity_id as parent_corporate_entity_id,
          edge.child_post_id,
          child_post.post_title as child_post_title,
          child_post.visibility_code as child_visibility_code,
          child_post.corporate_entity_id as child_corporate_entity_id,
          edge.fused_score
        from analysis_run_lineage_edge edge
        join source_post parent_post
          on parent_post.post_id = edge.parent_post_id
         and {SOURCE_POST_ELIGIBILITY_SQL.format(alias="parent_post")}
        join source_post child_post
          on child_post.post_id = edge.child_post_id
         and {SOURCE_POST_ELIGIBILITY_SQL.format(alias="child_post")}
        where edge.analysis_run_id = $1
        order by parent_post.post_title, child_post.post_title
        """,
        analysis_run_id,
    )
    return header["result_sha256"], [
        {
            "parent_post_id": str(row["parent_post_id"]),
            "parent_post_title": row["parent_post_title"],
            "child_post_id": str(row["child_post_id"]),
            "child_post_title": row["child_post_title"],
            "fused_score": float(row["fused_score"]),
        }
        for row in rows
        if reconstructed_edge_is_visible(
            parent_visibility_code=row["parent_visibility_code"],
            parent_corporate_entity_id=row["parent_corporate_entity_id"],
            child_visibility_code=row["child_visibility_code"],
            child_corporate_entity_id=row["child_corporate_entity_id"],
            affiliated_entity_ids=affiliated_entity_ids,
        )
    ]


async def persist_snapshot_members(
    conn: asyncpg.Connection,
    snapshot_id: Any,
    post_ids: list[str],
) -> None:
    """Freeze authorized post ids on a new snapshot. Skip a legacy database."""
    if not post_ids:
        return
    try:
        await conn.executemany(
            """
            insert into analysis_source_snapshot_member
                (analysis_source_snapshot_id, source_post_id)
            values ($1, $2)
            on conflict do nothing
            """,
            [(snapshot_id, post_id) for post_id in post_ids],
        )
    except asyncpg.UndefinedTableError:
        return


async def fetch_visible_scope_posts(
    conn: asyncpg.Connection,
    scope_kind_code: str,
    corporate_entity_id: Any,
    process_unit_id: Any,
    scope_key: str | None,
    affiliated_entity_ids: list[str],
    knowledge_cutoff: Any,
) -> list[dict[str, Any]]:
    """ABAC-visible post titles known at the run cutoff -- never a hidden body.

    ``knowledge_cutoff`` is the analysis clock (W3C Time / ISO 8601-1:2019;
    ADR 0013/0016). A later live post must not appear inside an earlier run.
    ``updated_at`` is compared separately so the operator can see which
    in-cutoff titles were rewritten after that clock. The live body is
    still not returned.
    """
    columns = (
        "post_id, post_title, visibility_code, corporate_entity_id, updated_at"
    )
    if scope_kind_code == "analysis_scope_corporate_entity" and corporate_entity_id:
        # Safe SQL: the selected columns and eligibility predicate are closed constants; ids are bound.
        rows = await conn.fetch(  # nosemgrep: python.lang.security.audit.sqli.asyncpg-sqli.asyncpg-sqli
            f"select {columns} "
            "from source_post where corporate_entity_id = $1 "
            "and created_at <= $2 "
            f"and {SOURCE_POST_ELIGIBILITY_SQL.format(alias='source_post')} "
            "order by created_at, post_title",
            corporate_entity_id,
            knowledge_cutoff,
        )
    elif scope_kind_code == "analysis_scope_process_unit" and process_unit_id:
        # Safe SQL: the selected columns and eligibility predicate are closed constants; ids are bound.
        rows = await conn.fetch(  # nosemgrep: python.lang.security.audit.sqli.asyncpg-sqli.asyncpg-sqli
            f"select {columns} "
            "from source_post where process_unit_id = $1 "
            "and created_at <= $2 "
            f"and {SOURCE_POST_ELIGIBILITY_SQL.format(alias='source_post')} "
            "order by created_at, post_title",
            process_unit_id,
            knowledge_cutoff,
        )
    elif scope_kind_code == "analysis_scope_thread_group" and scope_key:
        # Safe SQL: the selected columns and eligibility predicate are closed constants; keys are bound.
        rows = await conn.fetch(  # nosemgrep: python.lang.security.audit.sqli.asyncpg-sqli.asyncpg-sqli
            f"select {columns} "
            "from source_post where thread_group_key = $1 "
            "and created_at <= $2 "
            f"and {SOURCE_POST_ELIGIBILITY_SQL.format(alias='source_post')} "
            "order by created_at, post_title",
            scope_key,
            knowledge_cutoff,
        )
    elif scope_kind_code == "analysis_scope_all_visible":
        # Safe SQL: the selected columns and eligibility predicate are closed constants; cutoff is bound.
        rows = await conn.fetch(  # nosemgrep: python.lang.security.audit.sqli.asyncpg-sqli.asyncpg-sqli
            f"select {columns} "
            "from source_post where created_at <= $1 "
            f"and {SOURCE_POST_ELIGIBILITY_SQL.format(alias='source_post')} "
            "order by created_at, post_title",
            knowledge_cutoff,
        )
    else:
        return []
    affiliated = {str(entity_id) for entity_id in affiliated_entity_ids}
    posts: list[dict[str, Any]] = []
    for row in rows:
        visible = row["visibility_code"] == "public" or str(row["corporate_entity_id"]) in affiliated
        if not visible:
            continue
        updated_at = row["updated_at"]
        posts.append(
            {
                "post_id": str(row["post_id"]),
                "post_title": row["post_title"],
                "updated_at": _iso(updated_at),
                "live_after_cutoff": live_write_after_cutoff(
                    updated_at, knowledge_cutoff
                ),
            }
        )
    return posts


class AnalysisRunCreateError(Exception):
    """Fail-closed create: HTTP status plus a next-action detail string."""

    def __init__(self, status_code: int, detail: str) -> None:
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail


def _require_lineage_create_kind(run_kind_code: str) -> None:
    """Reject TEPP, topic-lineage, and report writes so this path cannot fake those products.

    TEPP and topic-lineage stay ``tepp_client`` wire paths (ADR 0022 /
    ADR 0132). Period reports stay on the Reports panel rebuild. A Pending
    TEPP or topic-lineage row that never called the transport is a
    fabricated measurement request.
    """
    if run_kind_code == _TEPP_RUN_KIND:
        raise AnalysisRunCreateError(
            422,
            "Open the failed temporal measurement, ask an administrator to restore analysis, then re-run it.",
        )
    if run_kind_code == _TOPIC_LINEAGE_RUN_KIND:
        raise AnalysisRunCreateError(
            422,
            "Open the failed topic journey analysis, ask an administrator to restore analysis, then re-run it.",
        )
    if run_kind_code == _REPORT_RUN_KIND:
        raise AnalysisRunCreateError(
            422,
            "Rebuild the period report from the Reports panel.",
        )
    if run_kind_code != _LINEAGE_RUN_KIND:
        raise AnalysisRunCreateError(
            422,
            "Only lineage reconstruction can be requested here.",
        )


@dataclass(frozen=True)
class AnalysisRunCapture:
    """Immutable capture plan for one authorized create (no source rows)."""

    snapshot_sha256: str
    maximum_available_time: datetime
    document_count: int
    thread_count: int
    configuration_sha256: str
    configuration_schema_version: str
    code_revision_sha: str


def utc_iso(value: datetime) -> str:
    """Normalize a timestamp to UTC ISO-8601 for digest stability."""
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).isoformat()


def plan_analysis_run_capture(
    *,
    run_kind_code: str,
    scope_kind_code: str,
    corporate_entity_id: str,
    knowledge_cutoff: datetime,
    idempotency_key: str,
    post_ids: list[str],
    thread_keys: list[str],
    latest_post_created_at: datetime | None,
    cutoff_explicit: bool = True,
) -> AnalysisRunCapture:
    """Hash the authorized cutoff bag. Never stores a post body or DSN.

    An omitted cutoff is hashed as ``unspecified`` so a retry of the same
    client key does not 409 just because the clock moved.
    """
    cutoff_token = utc_iso(knowledge_cutoff) if cutoff_explicit else "unspecified"
    snapshot_material = json.dumps(
        {
            "scope_kind_code": scope_kind_code,
            "corporate_entity_id": corporate_entity_id,
            "knowledge_cutoff": cutoff_token,
            "post_ids": sorted(post_ids),
        },
        separators=(",", ":"),
        sort_keys=True,
    )
    configuration_material = json.dumps(
        {
            "run_kind_code": run_kind_code,
            "scope_kind_code": scope_kind_code,
            "corporate_entity_id": corporate_entity_id,
            "knowledge_cutoff": cutoff_token,
            "idempotency_key": idempotency_key,
            "configuration_schema_version": _KIND_SCHEMA_VERSION[run_kind_code],
        },
        separators=(",", ":"),
        sort_keys=True,
    )
    available = latest_post_created_at if latest_post_created_at is not None else knowledge_cutoff
    return AnalysisRunCapture(
        snapshot_sha256=hashlib.sha256(snapshot_material.encode()).hexdigest(),
        maximum_available_time=available,
        document_count=len(post_ids),
        thread_count=len(set(thread_keys)),
        configuration_sha256=hashlib.sha256(configuration_material.encode()).hexdigest(),
        configuration_schema_version=_KIND_SCHEMA_VERSION[run_kind_code],
        code_revision_sha=hashlib.sha256(f"lineageweave-{PACKAGE_VERSION}".encode()).hexdigest(),
    )


def _canonical_idempotency_key(raw: str) -> str:
    """Trim and reject empty or control-bearing client keys."""
    key = raw.strip()
    if not key or len(key) > 256 or any(ord(char) < 32 for char in key):
        raise AnalysisRunCreateError(
            422,
            "Use a 1–256 character idempotency key without control characters, then retry.",
        )
    return key


def _resolve_corporate_entity_id(
    corporate_entity_id: str | None,
    affiliated_entity_ids: list[str],
) -> str:
    """Return the affiliated corp this run may cover, or a next-action error."""
    affiliated = [entity_id for entity_id in affiliated_entity_ids if entity_id]
    if corporate_entity_id:
        try:
            UUID(corporate_entity_id)
        except ValueError as exc:
            raise AnalysisRunCreateError(
                404,
                "This corporate entity is not visible to this account.",
            ) from exc
        if corporate_entity_id not in affiliated:
            raise AnalysisRunCreateError(
                404,
                "This corporate entity is not visible to this account.",
            )
        return corporate_entity_id
    if len(affiliated) != 1:
        raise AnalysisRunCreateError(
            422,
            "Choose the corporate entity this run should cover.",
        )
    return affiliated[0]


async def create_pending_analysis_run(
    conn: asyncpg.Connection,
    *,
    account_id: str,
    affiliated_entity_ids: list[str],
    run_kind_code: str,
    scope_kind_code: str,
    corporate_entity_id: str | None,
    knowledge_cutoff: datetime | None,
    idempotency_key: str,
) -> dict[str, Any]:
    """Insert snapshot, counts, frozen members, run, scope, and Pending.

    Lineage only. Does not reconstruct, call TEPP, or invent a theta.
    Kind rejection happens before any snapshot or run insert.
    Idempotent retries compare ``configuration_sha256``.
    """
    _require_lineage_create_kind(run_kind_code)
    if scope_kind_code != _CORPORATE_SCOPE:
        raise AnalysisRunCreateError(
            422,
            "Request a corporate-entity run. Other scopes are not available yet.",
        )
    cutoff_explicit = knowledge_cutoff is not None
    database_now = await conn.fetchval("select clock_timestamp()")
    if knowledge_cutoff is None:
        knowledge_cutoff = database_now
    elif knowledge_cutoff.tzinfo is None:
        knowledge_cutoff = knowledge_cutoff.replace(tzinfo=timezone.utc)
    if knowledge_cutoff > database_now:
        raise AnalysisRunCreateError(
            422,
            "Choose a knowledge cutoff at or before now, then request the run again.",
        )
    key = _canonical_idempotency_key(idempotency_key)
    corp_id = _resolve_corporate_entity_id(corporate_entity_id, affiliated_entity_ids)

    existing = await conn.fetchrow(
        """
        select analysis_run_id, configuration_sha256
        from analysis_run
        where requested_by_account_id = $1 and idempotency_key = $2
        """,
        account_id,
        key,
    )

    # Safe SQL: the eligibility predicate is an immutable schema fragment; corporate id and cutoff are bound.
    rows = await conn.fetch(  # nosemgrep: python.lang.security.audit.sqli.asyncpg-sqli.asyncpg-sqli
        f"""
        select post_id, post_title, thread_group_key, created_at,
               visibility_code, corporate_entity_id
        from source_post
        where corporate_entity_id = $1
          and created_at <= $2
          and {SOURCE_POST_ELIGIBILITY_SQL.format(alias="source_post")}
        order by created_at, post_title
        """,
        corp_id,
        knowledge_cutoff,
    )
    affiliated = {str(entity_id) for entity_id in affiliated_entity_ids}
    visible_rows = [
        row
        for row in rows
        if row["visibility_code"] == "public" or str(row["corporate_entity_id"]) in affiliated
    ]
    post_ids = [str(row["post_id"]) for row in visible_rows]
    thread_keys = [row["thread_group_key"] for row in visible_rows]
    latest = max((row["created_at"] for row in visible_rows), default=None)
    capture = plan_analysis_run_capture(
        run_kind_code=run_kind_code,
        scope_kind_code=scope_kind_code,
        corporate_entity_id=corp_id,
        knowledge_cutoff=knowledge_cutoff,
        idempotency_key=key,
        post_ids=post_ids,
        thread_keys=thread_keys,
        latest_post_created_at=latest,
        cutoff_explicit=cutoff_explicit,
    )
    if existing is not None:
        if existing["configuration_sha256"] != capture.configuration_sha256:
            raise AnalysisRunCreateError(
                409,
                "This request does not match the earlier run with the same key. "
                "Open that run, or retry with a new idempotency key.",
            )
        replayed = await fetch_visible_analysis_run(
            conn,
            str(existing["analysis_run_id"]),
            account_id,
            affiliated_entity_ids,
        )
        if replayed is None:
            raise AnalysisRunCreateError(404, "This analysis run is not visible.")
        return replayed

    snapshot_id = await conn.fetchval(
        """
        insert into analysis_source_snapshot
            (snapshot_sha256, source_contract_version,
             maximum_available_time, captured_at, created_at)
        values ($1, $2, $3, clock_timestamp(), clock_timestamp())
        on conflict (snapshot_sha256) do nothing
        returning analysis_source_snapshot_id
        """,
        capture.snapshot_sha256,
        _CAPTURE_CONTRACT_VERSION,
        capture.maximum_available_time,
    )
    if snapshot_id is None:
        snapshot_id = await conn.fetchval(
            """
            select analysis_source_snapshot_id
            from analysis_source_snapshot
            where snapshot_sha256 = $1
            for update
            """,
            capture.snapshot_sha256,
        )
    count_exists = await conn.fetchval(
        """
        select 1 from analysis_source_count
        where analysis_source_snapshot_id = $1
        limit 1
        """,
        snapshot_id,
    )
    if count_exists is None:
        await conn.execute(
            """
            insert into analysis_source_count
                (analysis_source_snapshot_id, count_type_code, count_value)
            values
                ($1, 'analysis_count_document', $2),
                ($1, 'analysis_count_thread', $3)
            """,
            snapshot_id,
            capture.document_count,
            capture.thread_count,
        )
    await persist_snapshot_members(conn, snapshot_id, post_ids)
    try:
        run_id = await conn.fetchval(
            """
            insert into analysis_run
                (analysis_source_snapshot_id, run_kind_code, idempotency_key,
                 requested_by_account_id, knowledge_cutoff,
                 configuration_schema_version, configuration_sha256,
                 code_revision_sha, requested_at)
            values ($1, $2, $3, $4, $5, $6, $7, $8, clock_timestamp())
            returning analysis_run_id
            """,
            snapshot_id,
            run_kind_code,
            key,
            account_id,
            knowledge_cutoff,
            capture.configuration_schema_version,
            capture.configuration_sha256,
            capture.code_revision_sha,
        )
    except asyncpg.UniqueViolationError:
        raced = await conn.fetchrow(
            """
            select analysis_run_id, configuration_sha256
            from analysis_run
            where requested_by_account_id = $1 and idempotency_key = $2
            """,
            account_id,
            key,
        )
        if raced is None or raced["configuration_sha256"] != capture.configuration_sha256:
            raise AnalysisRunCreateError(
                409,
                "This request does not match the earlier run with the same key. "
                "Open that run, or retry with a new idempotency key.",
            ) from None
        replayed = await fetch_visible_analysis_run(
            conn,
            str(raced["analysis_run_id"]),
            account_id,
            affiliated_entity_ids,
        )
        if replayed is None:
            raise AnalysisRunCreateError(404, "This analysis run is not visible.")
        return replayed
    await conn.execute(
        """
        insert into analysis_run_scope
            (analysis_run_id, scope_kind_code, corporate_entity_id)
        values ($1, $2, $3)
        """,
        run_id,
        scope_kind_code,
        corp_id,
    )
    await conn.execute(
        """
        insert into analysis_run_status_event
            (analysis_run_id, status_ordinal, status_code, occurred_at)
        values ($1, 1, 'analysis_status_pending', clock_timestamp())
        """,
        run_id,
    )
    created = await fetch_visible_analysis_run(
        conn,
        str(run_id),
        account_id,
        affiliated_entity_ids,
    )
    if created is None:
        raise AnalysisRunCreateError(404, "This analysis run is not visible.")
    return created
