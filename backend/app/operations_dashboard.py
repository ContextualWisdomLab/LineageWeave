"""ABAC-filtered projection of persisted operational case evidence."""

from __future__ import annotations

from datetime import date
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


class _Connection(Protocol):
    async def fetchrow(self, query: str, *args: object) -> Any:
        """Fetch one projected row."""
        pass

    async def fetch(self, query: str, *args: object) -> list[Any]:
        """Fetch projected rows."""
        pass


def _visible_period_sql(alias: str = "post") -> str:
    """Return the shared ABAC, eligibility, and event-clock predicate."""
    return f"""
        ({alias}.visibility_code = 'public'
         or ({alias}.corporate_entity_id::text = any($1::text[])
             and (cardinality($2::text[]) = 0
                  or {alias}.process_unit_id::text = any($2::text[]))))
        and {SOURCE_POST_ELIGIBILITY_SQL.format(alias=alias)}
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
    args = (list(corporate_entity_ids), list(process_unit_ids), period_start, period_end)
    visible = _visible_period_sql()
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
         where {visible}
         order by fact.post_id, fact.case_kind_code, fact.fact_ordinal
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
    total = int(metrics["total_post_count"])
    external = int(metrics["external_post_count"])
    case_post_ids: dict[str, set[str]] = {}
    case_event_counts: dict[str, int] = {}
    for row in case_rows:
        kind = row["case_kind_code"]
        case_post_ids.setdefault(kind, set()).add(str(row["post_id"]))
        case_event_counts[kind] = case_event_counts.get(kind, 0) + 1
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
        "cases": [
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
                "facts": facts.get((str(row["post_id"]), row["case_kind_code"]), []),
            }
            for row in case_rows
        ],
    }


def _period_label(period_start: date | None, period_end: date | None) -> str:
    """Format the exact event-time interval represented by the projection."""
    if period_start and period_end:
        return f"{period_start.isoformat()} ~ {period_end.isoformat()} · Event 발생일"
    if period_start:
        return f"{period_start.isoformat()} 이후 · Event 발생일"
    if period_end:
        return f"{period_end.isoformat()} 이전 · Event 발생일"
    return "전체 기간 · Event 발생일"
