"""ABAC-filtered projection of persisted operational case evidence."""

from __future__ import annotations

import hashlib
from datetime import date
from typing import Any, Protocol

from backend.app.post_eligibility import SOURCE_POST_ELIGIBILITY_SQL
from lineageweave.ontology import LW
from lineageweave.prov_o import PROV_RELATIONS


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
CASE_KIND_ONTOLOGY_CLASSES = {
    "claim_investigation": str(LW.ClaimInvestigation),
    "rebid_handover": str(LW.RebidHandover),
    "external_information": str(LW.ExternalInformation),
    "repeat_issue": str(LW.RepeatIssue),
}
EXTERNAL_RELATION_TARGETS = {
    "order": ("수주", str(LW.Order), str(LW.relatesToOrder)),
    "project": ("프로젝트", str(LW.Project), str(LW.relatesToProject)),
    "sales": ("영업", str(LW.SalesContext), str(LW.relatesToSales)),
    "business_management": (
        "사업 관리",
        str(LW.BusinessManagementContext),
        str(LW.relatesToBusinessManagement),
    ),
}
PROV_WAS_DERIVED_FROM = PROV_RELATIONS["wasDerivedFrom"].iri


def _operations_case_jsonld(
    post_id: str,
    case_kind_code: str,
    evidence_post_id: str,
    case_facts: list[dict[str, str]],
) -> dict[str, Any]:
    """Project one persisted case and its cited facts as bounded JSON-LD."""
    case_id = f"urn:lineageweave:operations-case:{post_id}:{case_kind_code}"
    statements: list[dict[str, Any]] = []
    for ordinal, fact in enumerate(case_facts):
        statement: dict[str, Any] = {
            "@id": f"{case_id}:fact:{ordinal}",
            "@type": [str(LW.OperationsCaseFact), "http://www.w3.org/ns/prov#Entity"],
            str(LW.factTypeCode): fact["fact_type_code"],
            str(LW.factValue): fact["value_text"],
            PROV_WAS_DERIVED_FROM: {
                "@id": f"urn:lineageweave:post:{fact['evidence_post_id']}"
            },
        }
        predicate = fact.get("relation_predicate_iri")
        target_class = fact.get("relation_target_class_iri")
        if predicate and target_class:
            target_digest = hashlib.sha256(
                f"{fact['relation_target_kind_code']}\0{fact['value_text']}".encode()
            ).hexdigest()
            statement.update(
                {
                    "http://www.w3.org/1999/02/22-rdf-syntax-ns#subject": {
                        "@id": case_id
                    },
                    "http://www.w3.org/1999/02/22-rdf-syntax-ns#predicate": {
                        "@id": predicate
                    },
                    "http://www.w3.org/1999/02/22-rdf-syntax-ns#object": {
                        "@id": f"urn:lineageweave:operations-target:{target_digest}",
                        "@type": target_class,
                        "http://www.w3.org/2000/01/rdf-schema#label": fact["value_text"],
                    },
                }
            )
        statements.append(statement)
    return {
        "@context": {
            "lw": str(LW),
            "prov": "http://www.w3.org/ns/prov#",
            "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
        },
        "@id": case_id,
        "@type": [CASE_KIND_ONTOLOGY_CLASSES[case_kind_code], "prov:Entity"],
        "prov:wasDerivedFrom": {
            "@id": f"urn:lineageweave:post:{evidence_post_id}"
        },
        str(LW.hasOperationsFact): statements,
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
    external_only: bool = False,
) -> dict[str, Any]:
    """Return quantified cases and their persisted source evidence."""
    if period_start and period_end and period_start > period_end:
        raise ValueError("period_start must not be after period_end")
    args = (list(corporate_entity_ids), list(process_unit_ids), period_start, period_end, external_only)
    visible = _visible_period_sql()
    metrics = await conn.fetchrow(
        f"""
        with visible_post as (
            select post.post_id
              from source_post post
             where {visible}
               and ($5::boolean is false or exists (
                   select 1
                     from operations_case_classification scoped_classification
                    where scoped_classification.post_id = post.post_id
                      and scoped_classification.case_kind_code = 'external_information'
               ))
        ), classified as (
            select classification.post_id, classification.case_kind_code
              from operations_case_classification classification
              join visible_post on visible_post.post_id = classification.post_id
        )
        select (select count(*) from visible_post) as total_post_count,
               (select count(*)
                  from post_summary_event summary_event
                 where exists (
                     select 1 from classified
                      where classified.post_id = summary_event.post_id
                 )) as total_event_count,
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
               coalesce(project.project_names, array[]::text[]) as project_names,
               (select count(*)::int
                  from post_summary_event summary_event
                 where summary_event.post_id = classification.post_id) as event_count
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
           and ($5::boolean is false or classification.case_kind_code = 'external_information')
         order by coalesce(post.event_occurred_at, post.created_at) desc,
                  classification.post_id, classification.case_kind_code
        """,
        *args,
    )
    fact_rows = await conn.fetch(
        f"""
        select fact.post_id, fact.case_kind_code, fact.fact_type_code,
               fact.value_text, fact.evidence_text, fact.evidence_post_id,
               fact.fact_ordinal, fact.relation_target_kind_code
          from operations_case_fact fact
          join source_post post on post.post_id = fact.post_id
         where {visible}
           and ($5::boolean is false or fact.case_kind_code = 'external_information')
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
           and ($5::boolean is false or missing.case_kind_code = 'external_information')
         order by missing.post_id, missing.case_kind_code, missing.fact_type_code
        """,
        *args,
    )
    facts: dict[tuple[str, str], list[dict[str, str]]] = {}
    for row in fact_rows:
        key = (str(row["post_id"]), row["case_kind_code"])
        projected_fact = {
            "fact_type_code": row["fact_type_code"],
            "fact_type_label": FACT_TYPE_LABELS[row["fact_type_code"]],
            "value_text": row["value_text"],
            "evidence_text": row["evidence_text"],
            "evidence_post_id": str(row["evidence_post_id"]),
            "ontology_class_iri": str(LW.OperationsCaseFact),
            "provenance_relation_iri": PROV_WAS_DERIVED_FROM,
        }
        target_kind = row["relation_target_kind_code"]
        if target_kind in EXTERNAL_RELATION_TARGETS:
            target_label, target_class, predicate = EXTERNAL_RELATION_TARGETS[target_kind]
            projected_fact["relation_target_kind_code"] = target_kind
            projected_fact["relation_target_kind_label"] = target_label
            projected_fact["relation_target_class_iri"] = target_class
            projected_fact["relation_predicate_iri"] = predicate
        facts.setdefault(key, []).append(projected_fact)
    missing_facts: dict[tuple[str, str], list[dict[str, str]]] = {}
    for row in missing_rows:
        key = (str(row["post_id"]), row["case_kind_code"])
        missing_facts.setdefault(key, []).append(
            {
                "fact_type_code": row["fact_type_code"],
                "fact_type_label": FACT_TYPE_LABELS[row["fact_type_code"]],
            }
        )
    total = int(metrics["total_post_count"])
    external = int(metrics["external_post_count"])
    case_post_ids: dict[str, set[str]] = {}
    case_event_counts: dict[str, int] = {}
    for row in case_rows:
        kind = row["case_kind_code"]
        case_post_ids.setdefault(kind, set()).add(str(row["post_id"]))
        case_event_counts[kind] = case_event_counts.get(kind, 0) + int(row["event_count"])
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
                "ontology_class_iri": CASE_KIND_ONTOLOGY_CLASSES[row["case_kind_code"]],
                "provenance_relation_iri": PROV_WAS_DERIVED_FROM,
                "occurred_at": row["occurred_at"].isoformat(),
                "facts": facts.get((str(row["post_id"]), row["case_kind_code"]), []),
                "missing_facts": missing_facts.get((str(row["post_id"]), row["case_kind_code"]), []),
                "semantic_projection": _operations_case_jsonld(
                    str(row["post_id"]),
                    row["case_kind_code"],
                    str(row["evidence_post_id"]),
                    facts.get((str(row["post_id"]), row["case_kind_code"]), []),
                ),
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
