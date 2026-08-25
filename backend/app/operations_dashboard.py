"""ABAC-filtered projection of persisted operational case evidence."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any, Protocol

from backend.app.post_eligibility import SOURCE_POST_ELIGIBILITY_SQL


CASE_KIND_LABELS = {
    "claim_investigation": "클레임 원인 규명",
    "rebid_handover": "재입찰 · 인수인계",
    "external_information": "발주 공고 · 시장 동향",
    "repeat_issue": "반복 이슈",
}
FACT_TYPE_LABELS = {
    "order": "발생 수주",
    "specification_change": "사양 변경",
    "originating_order": "원인 수주",
    "sales_pool": "수주 Pool",
    "discussion": "협의 내용",
    "counterparty": "협의 상대",
    "our_owner": "우리측 담당자",
    "decision": "후속 의사결정",
    "external_relation": "업무 관계",
    "issue_pattern": "반복 유형",
    "improvement_action": "개선 조치",
}
MILESTONE_TYPE_LABELS = {
    "claim_received": "클레임 접수",
    "cause_confirmed": "원인 확정",
    "rebid_response_requested": "재입찰 대응 요청",
    "rebid_decision_recorded": "재입찰 의사결정",
    "handover_started": "인수인계 시작",
    "handover_accepted": "인수 확인",
}
LIFECYCLE_DEFINITIONS = (
    (
        "claim_investigation",
        "claim_investigation",
        "클레임 원인 규명",
        "claim_received",
        "cause_confirmed",
    ),
    (
        "rebid_response",
        "rebid_handover",
        "재입찰 대응",
        "rebid_response_requested",
        "rebid_decision_recorded",
    ),
    (
        "handover_gap",
        "rebid_handover",
        "인수인계 공백",
        "handover_started",
        "handover_accepted",
    ),
)


class _Connection(Protocol):
    async def fetchrow(self, query: str, *args: object) -> Any:
        """Fetch one projected row."""
        pass

    async def fetch(self, query: str, *args: object) -> list[Any]:
        """Fetch projected rows."""
        pass


def _visible_scope_sql(alias: str = "post") -> str:
    """Return the shared ABAC and source-eligibility predicate."""
    return f"""
        ({alias}.visibility_code = 'public'
         or ({alias}.corporate_entity_id::text = any($1::text[])
             and (cardinality($2::text[]) = 0
                  or {alias}.process_unit_id::text = any($2::text[]))))
        and {SOURCE_POST_ELIGIBILITY_SQL.format(alias=alias)}
    """


def _visible_period_sql(alias: str = "post") -> str:
    """Return the shared visibility predicate plus the requested event interval."""
    return f"""
        {_visible_scope_sql(alias)}
        and ($3::date is null or (coalesce({alias}.event_occurred_at, {alias}.created_at)
             at time zone 'Asia/Seoul')::date >= $3)
        and ($4::date is null or (coalesce({alias}.event_occurred_at, {alias}.created_at)
             at time zone 'Asia/Seoul')::date <= $4)
    """


async def fetch_operations_dashboard(
    conn: _Connection,
    corporate_entity_ids: tuple[str, ...] | list[str],
    process_unit_ids: tuple[str, ...] | list[str] = (),
    period_start: date | None = None,
    period_end: date | None = None,
) -> dict[str, Any]:
    """Return quantified cases and their persisted source evidence."""
    if period_start and period_end and period_start > period_end:
        raise ValueError("period_start must not be after period_end")
    args = (
        list(corporate_entity_ids),
        list(process_unit_ids),
        period_start,
        period_end,
    )
    visible = _visible_period_sql()
    visible_evidence = _visible_scope_sql("evidence_post")
    metrics = await conn.fetchrow(
        f"""
        with visible_post as (
            select post.post_id
              from source_post post
             where {visible}
        ), classified as (
            select classification.post_id, classification.case_kind_code
              from operations_case_classification classification
              join visible_post on visible_post.post_id = classification.post_id
              join source_post evidence_post
                on evidence_post.post_id = classification.evidence_post_id
             where {visible_evidence}
        )
        select (select count(*) from visible_post) as total_post_count,
               (select count(*) from classified) as total_event_count,
               (select count(distinct post_id) from classified
                 where case_kind_code = 'external_information') as external_post_count,
               (select count(*) from visible_post
                 where not exists (
                     select 1 from operations_case_analysis analysis
                      where analysis.post_id = visible_post.post_id
                 ) and not exists (
                     select 1 from post_content_ingestion_job job
                      where job.post_id = visible_post.post_id
                        and job.status_code = 'post_content_ingestion_failed'
                 )) as pending_analysis_count,
               (select count(*) from visible_post
                  where exists (
                      select 1 from post_content_ingestion_job job
                       where job.post_id = visible_post.post_id
                         and job.status_code = 'post_content_ingestion_failed'
                  )) as failed_analysis_count
        """,
        *args,
    )
    case_rows = await conn.fetch(
        f"""
        select classification.post_id, classification.case_kind_code,
               classification.summary_text, classification.evidence_text,
               classification.evidence_post_id,
               coalesce(post.event_occurred_at, post.created_at) as occurred_at,
               coalesce(nullif(btrim(post.source_project_name), ''), project.primary_project_name)
                   as project_name,
               coalesce(project.project_names, array[]::text[]) as project_names
          from operations_case_classification classification
          join source_post post on post.post_id = classification.post_id
          join source_post evidence_post
            on evidence_post.post_id = classification.evidence_post_id
          left join lateral (
              select array_agg(names.project_name order by names.project_name) as project_names,
                     (
                         select nullif(btrim(primary_mention.project_name), '')
                           from post_project_mention primary_mention
                          where primary_mention.post_id = post.post_id
                            and nullif(btrim(primary_mention.project_name), '') is not null
                          order by primary_mention.confidence desc,
                                   primary_mention.project_name
                          limit 1
                     ) as primary_project_name
                from (
                    select nullif(btrim(post.source_project_name), '') as project_name
                    union
                    select nullif(btrim(mention.project_name), '')
                      from post_project_mention mention
                     where mention.post_id = post.post_id
                ) names
               where names.project_name is not null
          ) project on true
         where {visible}
           and {visible_evidence}
         order by coalesce(post.event_occurred_at, post.created_at) desc,
                  classification.post_id, classification.case_kind_code
        """,
        *args,
    )
    fact_rows = await conn.fetch(
        f"""
        select fact.post_id, fact.case_kind_code, fact.fact_type_code,
               fact.value_text, fact.evidence_text, fact.evidence_post_id,
               fact.fact_ordinal
          from operations_case_fact fact
          join source_post post on post.post_id = fact.post_id
          join source_post evidence_post on evidence_post.post_id = fact.evidence_post_id
         where {visible}
           and {visible_evidence}
         order by fact.post_id, fact.case_kind_code, fact.fact_ordinal
        """,
        *args,
    )
    missing_rows = await conn.fetch(
        f"""
        select missing.post_id, missing.case_kind_code, missing.fact_type_code
          from operations_case_missing_fact missing
          join source_post post on post.post_id = missing.post_id
         where {visible}
         order by missing.post_id, missing.case_kind_code, missing.fact_type_code
        """,
        *args,
    )
    milestone_rows = await conn.fetch(
        f"""
        select milestone.post_id, milestone.case_kind_code,
               milestone.milestone_type_code, milestone.evidence_text,
               milestone.evidence_post_id, milestone.observed_at,
               milestone.time_axis_code, false as is_missing
          from operations_case_milestone milestone
          join source_post post on post.post_id = milestone.post_id
          join source_post evidence_post on evidence_post.post_id = milestone.evidence_post_id
         where {visible}
           and {visible_evidence}
        union all
        select missing.post_id, missing.case_kind_code,
               missing.milestone_type_code, null, null, null, null, true
          from operations_case_missing_milestone missing
          join source_post post on post.post_id = missing.post_id
         where {visible}
         order by post_id, case_kind_code, milestone_type_code
        """,
        *args,
    )
    facts: dict[tuple[str, str], list[dict[str, str]]] = {}
    for row in fact_rows:
        key = (str(row["post_id"]), row["case_kind_code"])
        facts.setdefault(key, []).append(
            {
                "fact_type_code": row["fact_type_code"],
                "fact_type_label": FACT_TYPE_LABELS[row["fact_type_code"]],
                "value_text": row["value_text"],
                "evidence_text": row["evidence_text"],
                "evidence_post_id": str(row["evidence_post_id"]),
            }
        )
    missing_facts: dict[tuple[str, str], list[dict[str, str]]] = {}
    for row in missing_rows:
        key = (str(row["post_id"]), row["case_kind_code"])
        missing_facts.setdefault(key, []).append(
            {
                "fact_type_code": row["fact_type_code"],
                "fact_type_label": FACT_TYPE_LABELS[row["fact_type_code"]],
            }
        )
    milestones: dict[tuple[str, str], list[dict[str, Any]]] = {}
    missing_milestones: dict[tuple[str, str], set[str]] = {}
    for row in milestone_rows:
        key = (str(row["post_id"]), row["case_kind_code"])
        if row["is_missing"]:
            missing_milestones.setdefault(key, set()).add(row["milestone_type_code"])
            continue
        milestones.setdefault(key, []).append(
            {
                "milestone_type_code": row["milestone_type_code"],
                "milestone_type_label": MILESTONE_TYPE_LABELS[
                    row["milestone_type_code"]
                ],
                "evidence_text": row["evidence_text"],
                "evidence_post_id": str(row["evidence_post_id"]),
                "observed_at": row["observed_at"].isoformat(),
                "time_axis_code": row["time_axis_code"],
                "time_axis_label": (
                    "Event 발생일"
                    if row["time_axis_code"] == "event_occurred_at"
                    else "기록 생성일"
                ),
            }
        )
    total = int(metrics["total_post_count"])
    external = int(metrics["external_post_count"])
    case_post_ids: dict[str, set[str]] = {}
    case_event_counts: dict[str, int] = {}
    for row in case_rows:
        kind = row["case_kind_code"]
        case_post_ids.setdefault(kind, set()).add(str(row["post_id"]))
        case_event_counts[kind] = case_event_counts.get(kind, 0) + 1
    projected_cases = []
    lifecycle_metrics = {
        lifecycle_code: {
            "lifecycle_kind_code": lifecycle_code,
            "lifecycle_kind_label": label,
            "open_case_count": 0,
            "resolved_case_count": 0,
            "evidence_missing_case_count": 0,
        }
        for lifecycle_code, _case_kind, label, _start, _end in LIFECYCLE_DEFINITIONS
    }
    for row in case_rows:
        key = (str(row["post_id"]), row["case_kind_code"])
        case_milestones = milestones.get(key, [])
        case_lifecycles = _project_lifecycles(
            row["case_kind_code"], case_milestones, missing_milestones.get(key, set())
        )
        for lifecycle in case_lifecycles:
            lifecycle_metrics[lifecycle["lifecycle_kind_code"]][
                f"{lifecycle['status_code']}_case_count"
            ] += 1
        projected_cases.append(
            {
                "post_id": str(row["post_id"]),
                "case_kind_code": row["case_kind_code"],
                "case_kind_label": CASE_KIND_LABELS[row["case_kind_code"]],
                "project_name": row["project_name"],
                "project_names": list(row["project_names"]),
                "summary_text": row["summary_text"],
                "evidence_text": row["evidence_text"],
                "evidence_post_id": str(row["evidence_post_id"]),
                "occurred_at": row["occurred_at"].isoformat(),
                "facts": facts.get(key, []),
                "missing_facts": missing_facts.get(key, []),
                "milestones": case_milestones,
                "lifecycles": case_lifecycles,
            }
        )
    return {
        "period_label": _period_label(period_start, period_end),
        "total_post_count": total,
        "total_event_count": int(metrics["total_event_count"]),
        "external_post_count": external,
        "external_percent": external * 100 / total if total else 0.0,
        "pending_analysis_count": int(metrics["pending_analysis_count"]),
        "failed_analysis_count": int(metrics["failed_analysis_count"]),
        "case_metrics": [
            {
                "case_kind_code": kind,
                "case_kind_label": label,
                "event_count": case_event_counts.get(kind, 0),
                "post_count": len(case_post_ids.get(kind, set())),
            }
            for kind, label in CASE_KIND_LABELS.items()
        ],
        "lifecycle_metrics": list(lifecycle_metrics.values()),
        "cases": projected_cases,
    }


def _project_lifecycles(
    case_kind_code: str,
    milestones: list[dict[str, Any]],
    missing_milestones: set[str],
) -> list[dict[str, Any]]:
    """Pair only observed endpoints and return exact, threshold-free elapsed time."""
    by_type = {value["milestone_type_code"]: value for value in milestones}
    result = []
    for (
        lifecycle_code,
        required_case_kind,
        label,
        start_code,
        end_code,
    ) in LIFECYCLE_DEFINITIONS:
        if case_kind_code != required_case_kind:
            continue
        start = by_type.get(start_code)
        end = by_type.get(end_code)
        if start and end:
            elapsed_seconds = int(
                (
                    datetime.fromisoformat(end["observed_at"])
                    - datetime.fromisoformat(start["observed_at"])
                ).total_seconds()
            )
            status_code = "resolved"
            next_action = "시작·종료 Event 근거를 열어 경과 시간을 검토하세요."
        elif start and end_code in missing_milestones:
            elapsed_seconds = None
            status_code = "open"
            next_action = f"{MILESTONE_TYPE_LABELS[end_code]} Event 근거를 연결하세요."
        else:
            elapsed_seconds = None
            status_code = "evidence_missing"
            next_action = (
                f"{MILESTONE_TYPE_LABELS[start_code]} Event 근거를 연결하세요."
            )
        result.append(
            {
                "lifecycle_kind_code": lifecycle_code,
                "lifecycle_kind_label": label,
                "status_code": status_code,
                "status_label": {
                    "resolved": "종료 확인",
                    "open": "진행 중",
                    "evidence_missing": "측정 근거 부족",
                }[status_code],
                "started_at": start["observed_at"] if start else None,
                "resolved_at": end["observed_at"] if end else None,
                "elapsed_seconds": elapsed_seconds,
                "start_milestone": start,
                "end_milestone": end,
                "next_action_text": next_action,
            }
        )
    return result


def _period_label(period_start: date | None, period_end: date | None) -> str:
    """Format the exact event-time interval represented by the projection."""
    if period_start and period_end:
        return f"{period_start.isoformat()} ~ {period_end.isoformat()} · Event 발생일"
    if period_start:
        return f"{period_start.isoformat()} 이후 · Event 발생일"
    if period_end:
        return f"{period_end.isoformat()} 이전 · Event 발생일"
    return "전체 기간 · Event 발생일"
