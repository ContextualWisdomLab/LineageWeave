"""Authorized, source-redacting reads of the Milestone 2 analysis-run registry.

The registry itself is issue #89 / migration 0018. This module is the
product projection: an account sees only runs they requested or whose
scope they already have ABAC authority to walk. Aggregate counts and
lookup labels come back; source SQL, DSNs, raw records, and provider
payloads never do.
"""

from __future__ import annotations

from typing import Any

import asyncpg

from backend.app.knowledge_graph import labels_for_codes

_VISIBLE_RUN_SQL = """
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
          and (
            p.visibility_code = 'public'
            or p.corporate_entity_id = any($2::uuid[])
          )
      )
    )
"""

_RUN_SELECT = f"""
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
    where {{where}}
    order by run.requested_at desc
"""


def _iso(value: Any) -> str:
    """Serialize a timestamptz the same way post payloads do."""
    return value.isoformat() if hasattr(value, "isoformat") else str(value)


async def _counts_by_run(
    conn: asyncpg.Connection,
    run_ids: list[str],
) -> dict[str, list[asyncpg.Record]]:
    """Load aggregate snapshot counts for the given runs."""
    if not run_ids:
        return {}
    rows = await conn.fetch(
        """
        select run.analysis_run_id, counts.count_type_code, counts.count_value
        from analysis_run run
        join analysis_source_count counts
          on counts.analysis_source_snapshot_id = run.analysis_source_snapshot_id
        where run.analysis_run_id = any($1::uuid[])
        order by counts.count_type_code
        """,
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
        payload.append(item)
    return payload


async def fetch_visible_analysis_runs(
    conn: asyncpg.Connection,
    account_id: str,
    affiliated_entity_ids: list[str],
) -> list[dict[str, Any]]:
    """Runs the account requested or whose scope they may already walk."""
    rows = await conn.fetch(
        _RUN_SELECT.format(where=_VISIBLE_RUN_SQL),
        account_id,
        affiliated_entity_ids,
    )
    return await _serialize_runs(conn, rows)


async def fetch_visible_analysis_run(
    conn: asyncpg.Connection,
    analysis_run_id: str,
    account_id: str,
    affiliated_entity_ids: list[str],
) -> dict[str, Any] | None:
    """One visible run, or None when it is missing or hidden."""
    rows = await conn.fetch(
        _RUN_SELECT.format(
            where=f"run.analysis_run_id = $3 and ({_VISIBLE_RUN_SQL})"
        ),
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
    detail["visible_posts"] = await fetch_visible_scope_posts(
        conn,
        row["scope_kind_code"],
        row["corporate_entity_id"],
        row["process_unit_id"],
        row["scope_key"],
        affiliated_entity_ids,
        row["knowledge_cutoff"],
    )
    return detail


async def fetch_visible_scope_posts(
    conn: asyncpg.Connection,
    scope_kind_code: str,
    corporate_entity_id: Any,
    process_unit_id: Any,
    scope_key: str | None,
    affiliated_entity_ids: list[str],
    knowledge_cutoff: Any,
) -> list[dict[str, str]]:
    """ABAC-visible post titles known at the run cutoff -- never a hidden body.

    ``knowledge_cutoff`` is the analysis clock (W3C Time / ISO 8601-1:2019;
    ADR 0013/0016). A later live post must not appear inside an earlier run.
    """
    if scope_kind_code == "analysis_scope_corporate_entity" and corporate_entity_id:
        rows = await conn.fetch(
            "select post_id, post_title, visibility_code, corporate_entity_id "
            "from source_post where corporate_entity_id = $1 "
            "and created_at <= $2 "
            "order by created_at, post_title",
            corporate_entity_id,
            knowledge_cutoff,
        )
    elif scope_kind_code == "analysis_scope_process_unit" and process_unit_id:
        rows = await conn.fetch(
            "select post_id, post_title, visibility_code, corporate_entity_id "
            "from source_post where process_unit_id = $1 "
            "and created_at <= $2 "
            "order by created_at, post_title",
            process_unit_id,
            knowledge_cutoff,
        )
    elif scope_kind_code == "analysis_scope_thread_group" and scope_key:
        rows = await conn.fetch(
            "select post_id, post_title, visibility_code, corporate_entity_id "
            "from source_post where thread_group_key = $1 "
            "and created_at <= $2 "
            "order by created_at, post_title",
            scope_key,
            knowledge_cutoff,
        )
    elif scope_kind_code == "analysis_scope_all_visible":
        rows = await conn.fetch(
            "select post_id, post_title, visibility_code, corporate_entity_id "
            "from source_post where created_at <= $1 "
            "order by created_at, post_title",
            knowledge_cutoff,
        )
    else:
        return []
    affiliated = {str(entity_id) for entity_id in affiliated_entity_ids}
    posts: list[dict[str, str]] = []
    for row in rows:
        visible = row["visibility_code"] == "public" or str(row["corporate_entity_id"]) in affiliated
        if not visible:
            continue
        posts.append({"post_id": str(row["post_id"]), "post_title": row["post_title"]})
    return posts
