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
    database_connection: _Connection,
    corporate_entity_ids: tuple[str, ...] | list[str],
    process_unit_ids: tuple[str, ...] | list[str] = (),
    period_start: date | None = None,
    period_end: date | None = None,
) -> dict[str, Any]:
    """Return quantified cases and their persisted source evidence."""
    if period_start and period_end and period_start > period_end:
        raise ValueError("period_start must not be after period_end")
    query_parameters = (
        list(corporate_entity_ids),
        list(process_unit_ids),
        period_start,
        period_end,
    )
    visible_period_predicate = _visible_period_sql()
    dashboard_metrics = await database_connection.fetchrow(
        f"""
        with visible_post as (
            select post.post_id
              from source_post post
             where {visible_period_predicate}
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
        *query_parameters,
    )
    operations_case_rows = await database_connection.fetch(
        f"""
        select classification.post_id, classification.case_kind_code,
               classification.summary_text, classification.evidence_text,
               classification.evidence_post_id,
               coalesce(post.event_occurred_at, post.created_at) as occurred_at,
               coalesce(nullif(btrim(post.source_project_name), ''), project.project_name)
                   as project_name
          from operations_case_classification classification
          join source_post post on post.post_id = classification.post_id
          left join lateral (
              select mention.project_name
                from post_project_mention mention
               where mention.post_id = post.post_id
               order by mention.confidence desc, mention.project_name, mention.project_key
               limit 1
          ) project on true
         where {visible_period_predicate}
         order by coalesce(post.event_occurred_at, post.created_at) desc,
                  classification.post_id, classification.case_kind_code
        """,
        *query_parameters,
    )
    operations_case_fact_rows = await database_connection.fetch(
        f"""
        select fact.post_id, fact.case_kind_code, fact.fact_type_code,
               fact.value_text, fact.evidence_text, fact.evidence_post_id,
               fact.fact_ordinal
          from operations_case_fact fact
          join source_post post on post.post_id = fact.post_id
         where {visible_period_predicate}
         order by fact.post_id, fact.case_kind_code, fact.fact_ordinal
        """,
        *query_parameters,
    )
    operations_case_facts: dict[tuple[str, str], list[dict[str, str]]] = {}
    for fact_row in operations_case_fact_rows:
        case_identity = (str(fact_row["post_id"]), fact_row["case_kind_code"])
        operations_case_facts.setdefault(case_identity, []).append(
            {
                "fact_type_code": fact_row["fact_type_code"],
                "fact_type_label": FACT_TYPE_LABELS[fact_row["fact_type_code"]],
                "value_text": fact_row["value_text"],
                "evidence_text": fact_row["evidence_text"],
                "evidence_post_id": str(fact_row["evidence_post_id"]),
            }
        )
    total_post_count = int(dashboard_metrics["total_post_count"])
    external_post_count = int(dashboard_metrics["external_post_count"])
    return {
        "period_label": _period_label(period_start, period_end),
        "total_post_count": total_post_count,
        "total_event_count": int(dashboard_metrics["total_event_count"]),
        "external_post_count": external_post_count,
        "external_percent": (
            external_post_count * 100 / total_post_count if total_post_count else 0.0
        ),
        "pending_analysis_count": int(dashboard_metrics["pending_analysis_count"]),
        "failed_analysis_count": int(dashboard_metrics["failed_analysis_count"]),
        "cases": [
            {
                "post_id": str(case_row["post_id"]),
                "case_kind_code": case_row["case_kind_code"],
                "case_kind_label": CASE_KIND_LABELS[case_row["case_kind_code"]],
                "project_name": case_row["project_name"],
                "summary_text": case_row["summary_text"],
                "evidence_text": case_row["evidence_text"],
                "evidence_post_id": str(case_row["evidence_post_id"]),
                "occurred_at": case_row["occurred_at"].isoformat(),
                "facts": operations_case_facts.get(
                    (str(case_row["post_id"]), case_row["case_kind_code"]), []
                ),
            }
            for case_row in operations_case_rows
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
