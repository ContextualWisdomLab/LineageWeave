"""ABAC-filtered projection of persisted operational case evidence."""

from __future__ import annotations

from datetime import date, datetime
import json
from typing import Any, Protocol

from backend.app.post_eligibility import SOURCE_POST_ELIGIBILITY_SQL
from lineageweave.ontology import LW
from lineageweave.operations_case_analysis import REQUIRED_FACT_TYPES
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
MILESTONE_TYPE_LABELS = {
    "claim_received": "클레임 접수",
    "cause_confirmed": "원인 확정",
    "rebid_response_requested": "재입찰 대응 요청",
    "rebid_decision_recorded": "재입찰 의사결정",
    "handover_started": "인수인계 시작",
    "handover_accepted": "인수 확인",
}
LIFECYCLE_DEFINITIONS = (
    ("claim_investigation", "claim_investigation", "클레임 원인 규명", "claim_received", "cause_confirmed"),
    ("rebid_response", "rebid_handover", "재입찰 대응", "rebid_response_requested", "rebid_decision_recorded"),
    ("handover_gap", "rebid_handover", "인수인계 공백", "handover_started", "handover_accepted"),
)
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
                "@id": f"urn:lineageweave:post:{fact['evidence_post_id']}",
                "@type": [str(LW.Post), "http://www.w3.org/ns/prov#Entity"],
            },
        }
        predicate = fact.get("relation_predicate_iri")
        target_class = fact.get("relation_target_class_iri")
        if predicate and target_class:
            statement.update(
                {
                    "http://www.w3.org/1999/02/22-rdf-syntax-ns#subject": {
                        "@id": case_id
                    },
                    "http://www.w3.org/1999/02/22-rdf-syntax-ns#predicate": {
                        "@id": predicate
                    },
                    "http://www.w3.org/1999/02/22-rdf-syntax-ns#object": {
                        "@id": f"{case_id}:fact:{ordinal}:target",
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
            "@id": f"urn:lineageweave:post:{evidence_post_id}",
            "@type": [str(LW.Post), "prov:Entity"],
        },
        str(LW.hasOperationsFact): statements,
    }


class _Connection(Protocol):
    async def fetchrow(self, query: str, *args: object) -> Any:
        """Fetch one projected row."""
        pass  # pragma: no cover - structural Protocol member

    async def fetch(self, query: str, *args: object) -> list[Any]:
        """Fetch projected rows."""
        pass  # pragma: no cover - structural Protocol member


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
    external_only: bool = False,
) -> dict[str, Any]:
    """Return quantified cases and their persisted source evidence."""
    if period_start and period_end and period_start > period_end:
        raise ValueError("period_start must not be after period_end")
    args = (list(corporate_entity_ids), list(process_unit_ids), period_start, period_end, external_only)
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
        ), scoped_post as (
            select visible_post.post_id
              from visible_post
             where $5::boolean is false
                or exists (
                    select 1
                      from classified
                     where classified.post_id = visible_post.post_id
                       and classified.case_kind_code = 'external_information'
                )
        )
        select (select count(*) from visible_post) as total_post_count,
               (select count(*)
                  from post_summary_event summary_event
                 where exists (
                     select 1 from classified
                      where classified.post_id = summary_event.post_id
                        and ($5::boolean is false
                             or classified.case_kind_code = 'external_information')
                 )) as total_event_count,
               (select count(distinct post_id) from classified
                 where case_kind_code = 'external_information') as external_post_count,
               (select count(*) from scoped_post
                 where not exists (
                     select 1 from operations_case_analysis analysis
                      where analysis.post_id = scoped_post.post_id
                 ) and not exists (
                     select 1 from post_content_ingestion_job job
                      where job.post_id = scoped_post.post_id
                        and job.status_code = 'post_content_ingestion_failed'
                 )) as pending_analysis_count,
               (select count(*) from scoped_post
                  where exists (
                      select 1 from post_content_ingestion_job job
                       where job.post_id = scoped_post.post_id
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
          join source_post evidence_post on evidence_post.post_id = fact.evidence_post_id
         where {visible}
           and {visible_evidence}
           and ($5::boolean is false or fact.case_kind_code = 'external_information')
         order by fact.post_id, fact.case_kind_code, fact.fact_ordinal
        """,
        *args,
    )
    product_relation_rows = await conn.fetch(
        f"""
        select relation.post_id, relation.case_kind_code, relation.fact_ordinal,
               relation.relation_type_code, mention.extracted_product_name,
               catalog.canonical_product_name, relation.evidence_text,
               relation.evidence_post_id
          from product_operations_fact_relation relation
          join post_product_mention mention
            on mention.post_id = relation.post_id
           and mention.mention_ordinal = relation.mention_ordinal
          left join product_catalog catalog
            on catalog.product_catalog_id = mention.product_catalog_id
          join source_post post on post.post_id = relation.post_id
          join source_post evidence_post on evidence_post.post_id = relation.evidence_post_id
         where {visible}
           and {visible_evidence}
           and ($5::boolean is false or relation.case_kind_code = 'external_information')
         order by relation.post_id, relation.case_kind_code, relation.fact_ordinal,
                  relation.mention_ordinal
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
        union all
        select fact.post_id, fact.case_kind_code, fact.fact_type_code
          from operations_case_fact fact
          join source_post post on post.post_id = fact.post_id
          join source_post evidence_post on evidence_post.post_id = fact.evidence_post_id
         where {visible}
           and not ({visible_evidence})
           and ($6::jsonb -> fact.case_kind_code) ? fact.fact_type_code
           and ($5::boolean is false or fact.case_kind_code = 'external_information')
         order by post_id, case_kind_code, fact_type_code
        """,
        *args,
        json.dumps(
            {
                case_kind: sorted(fact_types)
                for case_kind, fact_types in REQUIRED_FACT_TYPES.items()
            }
        ),
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
           and ($5::boolean is false or milestone.case_kind_code = 'external_information')
        union all
        select missing.post_id, missing.case_kind_code,
               missing.milestone_type_code, null, null, null, null, true
          from operations_case_missing_milestone missing
          join source_post post on post.post_id = missing.post_id
         where {visible}
           and ($5::boolean is false or missing.case_kind_code = 'external_information')
         order by post_id, case_kind_code, observed_at nulls last,
                  milestone_type_code
        """,
        *args,
    )
    topic_context = (
        {
            "status_code": "not_applicable",
            "reason_code": "external_information_view",
            "next_action": "전체 Dashboard로 전환해 주요 글과 조직별 변화를 확인하세요.",
            "required_contracts": [],
            "model_run": None,
            "topics": [],
        }
        if external_only
        else await _fetch_topic_context_dashboard(conn, visible, args[:4])
    )
    product_relations: dict[tuple[str, str, int], list[dict[str, str]]] = {}
    for row in product_relation_rows:
        relation_key = (
            str(row["post_id"]),
            row["case_kind_code"],
            int(row["fact_ordinal"]),
        )
        product_relations.setdefault(relation_key, []).append(
            {
                "relation_type_code": row["relation_type_code"],
                "product_name": row["canonical_product_name"]
                or row["extracted_product_name"],
                "evidence_text": row["evidence_text"],
                "evidence_post_id": str(row["evidence_post_id"]),
            }
        )
    facts: dict[tuple[str, str], list[dict[str, Any]]] = {}
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
        related_products = product_relations.get(
            (str(row["post_id"]), row["case_kind_code"], int(row["fact_ordinal"])),
            [],
        )
        if related_products:
            projected_fact["product_relations"] = related_products
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
                    "사건 발생일"
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
        case_event_counts[kind] = case_event_counts.get(kind, 0) + int(row["event_count"])
    projected_cases = []
    lifecycle_metrics = {
        lifecycle_code: {
            "lifecycle_kind_code": lifecycle_code,
            "lifecycle_kind_label": label,
            "open_case_count": 0,
            "resolved_case_count": 0,
            "evidence_missing_case_count": 0,
        }
        for lifecycle_code, _kind, label, _start, _end in LIFECYCLE_DEFINITIONS
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
                "ontology_class_iri": CASE_KIND_ONTOLOGY_CLASSES[row["case_kind_code"]],
                "provenance_relation_iri": PROV_WAS_DERIVED_FROM,
                "occurred_at": row["occurred_at"].isoformat(),
                "facts": facts.get(key, []),
                "missing_facts": missing_facts.get(key, []),
                "milestones": case_milestones,
                "lifecycles": case_lifecycles,
                "semantic_projection": _operations_case_jsonld(
                    str(row["post_id"]), row["case_kind_code"],
                    str(row["evidence_post_id"]), facts.get(key, []),
                ),
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
        "topic_context": topic_context,
        "lifecycle_metrics": list(lifecycle_metrics.values()),
        "cases": projected_cases,
    }


def _project_lifecycles(
    case_kind_code: str,
    milestones: list[dict[str, Any]],
    missing_milestones: set[str],
) -> list[dict[str, Any]]:
    """Pair observed endpoints and report exact elapsed time without thresholds."""
    by_type = {value["milestone_type_code"]: value for value in milestones}
    result = []
    for lifecycle_code, required_kind, label, start_code, end_code in LIFECYCLE_DEFINITIONS:
        if case_kind_code != required_kind:
            continue
        start = by_type.get(start_code)
        end = by_type.get(end_code)
        if start and end:
            elapsed_seconds = int((datetime.fromisoformat(end["observed_at"]) - datetime.fromisoformat(start["observed_at"])).total_seconds())
            status_code = "resolved"
            next_action = "시작·종료 사건 근거를 열어 경과 시간을 검토하세요."
        elif start:
            elapsed_seconds = None
            status_code = "open"
            next_action = f"{MILESTONE_TYPE_LABELS[end_code]} Event 근거를 연결하세요."
        else:
            elapsed_seconds = None
            status_code = "evidence_missing"
            next_action = f"{MILESTONE_TYPE_LABELS[start_code]} Event 근거를 연결하세요."
        result.append({
            "lifecycle_kind_code": lifecycle_code,
            "lifecycle_kind_label": label,
            "status_code": status_code,
            "status_label": {"resolved": "종료 확인", "open": "진행 중", "evidence_missing": "측정 근거 부족"}[status_code],
            "started_at": start["observed_at"] if start else None,
            "resolved_at": end["observed_at"] if end else None,
            "elapsed_seconds": elapsed_seconds,
            "start_milestone": start,
            "end_milestone": end,
            "next_action_text": next_action,
        })
    return result


async def _fetch_topic_context_dashboard(
    conn: _Connection,
    visible_post_sql: str,
    args: tuple[object, ...],
) -> dict[str, Any]:
    """Project exact accepted producer rows or an actionable unavailable state."""
    authorized_model_scope = """
        ((scope.scope_kind_code = 'analysis_scope_corporate_entity'
          and scope.corporate_entity_id::text = any($1::text[])
          and cardinality($2::text[]) = 0)
         or
         (scope.scope_kind_code = 'analysis_scope_process_unit'
          and scope.process_unit_id::text = any($2::text[])))
    """
    readiness = await conn.fetchrow(
        f"""
        with visible_post as (
            select post.post_id,
                   coalesce(post.event_occurred_at, post.created_at) as occurred_at
              from source_post post
             where {visible_post_sql}
        )
        select exists (
                   select 1
                     from topic_context_membership membership
                     join topic_model_run model
                       on model.topic_model_run_id = membership.topic_model_run_id
                     join analysis_run analysis on analysis.analysis_run_id = model.analysis_run_id
                     join analysis_run_scope scope on scope.analysis_run_id = analysis.analysis_run_id
                     join visible_post on visible_post.post_id = membership.source_post_id
                    where visible_post.occurred_at >= membership.valid_from
                      and visible_post.occurred_at < membership.valid_to
                      and {authorized_model_scope}
               ) as tepp_posterior_persisted,
               exists (
                   select 1
                     from topic_post_context_influence influence
                     join topic_context_membership membership
                       on membership.topic_model_run_id = influence.topic_model_run_id
                      and membership.topic_context_membership_id = influence.topic_context_membership_id
                     join topic_model_run model
                       on model.topic_model_run_id = influence.topic_model_run_id
                     join analysis_run analysis on analysis.analysis_run_id = model.analysis_run_id
                     join analysis_run_scope scope on scope.analysis_run_id = analysis.analysis_run_id
                     join visible_post on visible_post.post_id = membership.source_post_id
                     join topic_activity_interval activity
                       on activity.topic_model_run_id = influence.topic_model_run_id
                      and activity.topic_index = influence.topic_index
                      and visible_post.occurred_at >= activity.valid_from
                      and visible_post.occurred_at < activity.valid_to
                    where visible_post.occurred_at >= membership.valid_from
                      and visible_post.occurred_at < membership.valid_to
                      and {authorized_model_scope}
               ) as fast_mlsirm_influence_persisted
        """,
        *args,
    )
    rows = await conn.fetch(
        f"""
        with visible_post as (
            select post.post_id,
                   coalesce(post.event_occurred_at, post.created_at) as occurred_at
              from source_post post
             where {visible_post_sql}
        ), candidate_runs as (
            select model.topic_model_run_id,
                   influence_run.topic_influence_run_id,
                   influence_run.accepted_at
              from topic_model_run model
              join analysis_run analysis on analysis.analysis_run_id = model.analysis_run_id
              join analysis_run_scope scope on scope.analysis_run_id = analysis.analysis_run_id
              join topic_influence_run influence_run
                on influence_run.topic_model_run_id = model.topic_model_run_id
             where {authorized_model_scope}
        ), selected as (
            select *
              from candidate_runs
             order by accepted_at desc, topic_model_run_id, topic_influence_run_id
             limit 1
        ), eligible as (
            select model.topic_model_run_id, model.tepp_run_id, model.tepp_snapshot_id,
                   model.tepp_schema_version, model.tepp_model_contract_version,
                   model.tepp_artifact_sha256, model.posterior_draw_set_id,
                   model.posterior_draw_count, model.topic_count,
                   snapshot.snapshot_sha256 as source_snapshot_sha256,
                   analysis.knowledge_cutoff,
                   influence_run.topic_influence_run_id,
                   influence_run.fast_mlsirm_schema_version,
                   influence_run.fast_mlsirm_version,
                   influence_run.fast_mlsirm_code_revision,
                   influence_run.fast_mlsirm_artifact_sha256,
                   influence_run.compute_backend_code,
                   influence_run.precision_code,
                   influence_run.membership_fingerprint_sha256,
                   influence.topic_index, activity.state_code,
                   activity.valid_from as activity_valid_from,
                   activity.valid_to as activity_valid_to,
                   membership.dimension_code, membership.context_id,
                   context.context_label, membership.membership_weight,
                   membership_evidence.node_id as membership_evidence_post_id,
                   membership.source_post_id, visible_post.occurred_at,
                   influence.influence_value,
                   influence.uncertainty_method_code,
                   influence.uncertainty_lower_value,
                   influence.uncertainty_upper_value,
                   influence.diagnostic_status_code,
                   influence_run.accepted_at,
                   visible_post.post_id is not null
                   and activity.topic_model_run_id is not null
                   and membership_evidence_visible.post_id is not null
                   and not exists (
                       select 1
                         from topic_lineage_relation checked_relation
                         left join provenance_assertion checked_assertion
                           on checked_assertion.assertion_id = checked_relation.provenance_assertion_id
                         left join provenance_resource_binding checked_evidence
                           on checked_evidence.resource_id = checked_assertion.object_resource_id
                          and checked_evidence.node_type_code = 'node_post'
                         left join visible_post checked_visible
                           on checked_visible.post_id = checked_evidence.node_id
                        where checked_relation.topic_model_run_id = selected.topic_model_run_id
                          and checked_visible.post_id is null
                   ) as provenance_complete
              from topic_post_context_influence influence
              join topic_influence_run influence_run
                on influence_run.topic_model_run_id = influence.topic_model_run_id
               and influence_run.topic_influence_run_id = influence.topic_influence_run_id
              join selected
                on selected.topic_model_run_id = influence.topic_model_run_id
               and selected.topic_influence_run_id = influence.topic_influence_run_id
              join topic_model_run model
                on model.topic_model_run_id = selected.topic_model_run_id
              join analysis_run analysis on analysis.analysis_run_id = model.analysis_run_id
              join analysis_source_snapshot snapshot
                on snapshot.analysis_source_snapshot_id = analysis.analysis_source_snapshot_id
              join topic_context_membership membership
                on membership.topic_model_run_id = influence.topic_model_run_id
               and membership.topic_context_membership_id = influence.topic_context_membership_id
              join topic_context_definition context
                on context.topic_model_run_id = membership.topic_model_run_id
               and context.dimension_code = membership.dimension_code
               and context.context_id = membership.context_id
              left join visible_post on visible_post.post_id = membership.source_post_id
              left join provenance_assertion membership_assertion
                on membership_assertion.assertion_id = membership.provenance_assertion_id
              left join provenance_resource_binding membership_evidence
                on membership_evidence.resource_id = membership_assertion.object_resource_id
               and membership_evidence.node_type_code = 'node_post'
              left join visible_post membership_evidence_visible
                on membership_evidence_visible.post_id = membership_evidence.node_id
              left join topic_activity_interval activity
                on activity.topic_model_run_id = influence.topic_model_run_id
               and activity.topic_index = influence.topic_index
               and visible_post.occurred_at >= activity.valid_from
               and visible_post.occurred_at < activity.valid_to
               and visible_post.occurred_at >= membership.valid_from
               and visible_post.occurred_at < membership.valid_to
        )
        select eligible.*,
               coalesce((
                   select jsonb_agg(jsonb_build_object(
                              'event_code', relation.event_code,
                              'source_topic_index', relation.source_topic_index,
                              'target_topic_index', relation.target_topic_index,
                              'event_time', relation.event_time,
                              'evidence_post_id', relation_evidence.node_id
                          ) order by relation.event_time, relation.relation_ordinal)
                     from topic_lineage_relation relation
                     join provenance_assertion relation_assertion
                       on relation_assertion.assertion_id = relation.provenance_assertion_id
                     join provenance_resource_binding relation_evidence
                       on relation_evidence.resource_id = relation_assertion.object_resource_id
                      and relation_evidence.node_type_code = 'node_post'
                     join visible_post relation_evidence_visible
                       on relation_evidence_visible.post_id = relation_evidence.node_id
                    where relation.topic_model_run_id = eligible.topic_model_run_id
                      and (relation.source_topic_index = eligible.topic_index
                           or relation.target_topic_index = eligible.topic_index)
               ), '[]'::jsonb) as lineage_events
          from eligible
         order by eligible.topic_index,
                  case eligible.dimension_code
                      when 'business_unit' then 0
                      when 'process_unit' then 1
                      when 'team' then 2
                      else 3
                  end,
                  eligible.context_label,
                  eligible.influence_value desc,
                  eligible.occurred_at,
                  eligible.source_post_id
        """,
        *args,
    )
    if not rows:
        tepp_ready = bool(readiness and readiness["tepp_posterior_persisted"])
        # The readiness query can see an accepted influence row from a
        # different selected run than the projection query.  In an empty
        # projection, report fast-mlsirm as unavailable for this exact
        # visible/time window rather than claiming a persisted contract.
        fast_mlsirm_ready = False
        return {
            "status_code": "unavailable",
            "reason_code": (
                "fast_mlsirm_influence_not_persisted"
                if tepp_ready
                else "tepp_topic_posterior_not_persisted"
            ),
            "next_action": (
                "선택한 범위의 글 영향도 분석 결과를 먼저 완료하세요."
                if tepp_ready
                else "선택한 범위의 시간 흐름 분석 결과를 먼저 완료하세요."
            ),
            "required_contracts": [
                {
                    "authority": "TEPP",
                    "schema_version": "tepp.topic_context_posterior.v1",
                    "state_code": "persisted" if tepp_ready else "not_persisted",
                },
                {
                    "authority": "fast-mlsirm",
                    "schema_version": "fast_mlsirm.topic_context_influence.v1",
                    "state_code": (
                        "persisted"
                        if fast_mlsirm_ready
                        else "not_persisted"
                    ),
                },
            ],
            "model_run": None,
            "topics": [],
        }

    if not all(bool(row["provenance_complete"]) for row in rows):
        return {
            "status_code": "unavailable",
            "reason_code": "topic_context_provenance_not_navigable",
            "next_action": "조직 소속과 주제 변화의 근거 글 연결을 완료한 뒤 다시 확인하세요.",
            "required_contracts": [
                {
                    "authority": "TEPP",
                    "schema_version": rows[0]["tepp_schema_version"],
                    "state_code": "evidence_link_unavailable",
                },
                {
                    "authority": "fast-mlsirm",
                    "schema_version": rows[0]["fast_mlsirm_schema_version"],
                    "state_code": "evidence_link_unavailable",
                },
            ],
            "model_run": None,
            "topics": [],
        }

    first = rows[0]
    topics: dict[int, dict[str, Any]] = {}
    for row in rows:
        topic_index = int(row["topic_index"])
        raw_lineage_events = row["lineage_events"]
        lineage_events = (
            json.loads(raw_lineage_events)
            if isinstance(raw_lineage_events, str)
            else list(raw_lineage_events)
        )
        topic = topics.setdefault(
            topic_index,
            {
                "topic_index": topic_index,
                "activity_intervals": [],
                "lineage_events": lineage_events,
                "contexts": [],
            },
        )
        interval = {
            "state_code": row["state_code"],
            "valid_from": row["activity_valid_from"].isoformat(),
            "valid_to": row["activity_valid_to"].isoformat(),
        }
        if interval not in topic["activity_intervals"]:
            topic["activity_intervals"].append(interval)
        context_key = (row["dimension_code"], row["context_id"])
        context = next(
            (
                item
                for item in topic["contexts"]
                if (item["dimension_code"], item["context_id"]) == context_key
            ),
            None,
        )
        if context is None:
            context = {
                "dimension_code": row["dimension_code"],
                "context_id": row["context_id"],
                "context_label": row["context_label"],
                "influences": [],
            }
            topic["contexts"].append(context)
        context["influences"].append(
            {
                "post_id": str(row["source_post_id"]),
                "occurred_at": row["occurred_at"].isoformat(),
                "topic_state_code": row["state_code"],
                "model_influence": float(row["influence_value"]),
                "uncertainty_method_code": row["uncertainty_method_code"],
                "uncertainty_lower_value": float(row["uncertainty_lower_value"]),
                "uncertainty_upper_value": float(row["uncertainty_upper_value"]),
                "diagnostic_status_code": row["diagnostic_status_code"],
                "membership_weight": float(row["membership_weight"]),
                "membership_evidence_post_id": str(row["membership_evidence_post_id"]),
            }
        )

    return {
        "status_code": "accepted",
        "reason_code": None,
        "next_action": "주제와 조직 범위를 선택해 영향이 큰 글과 근거를 확인하세요.",
        "required_contracts": [
            {"authority": "TEPP", "schema_version": first["tepp_schema_version"], "state_code": "persisted"},
            {"authority": "fast-mlsirm", "schema_version": first["fast_mlsirm_schema_version"], "state_code": "persisted"},
        ],
        "model_run": {
            "tepp_run_id": first["tepp_run_id"],
            "tepp_snapshot_id": first["tepp_snapshot_id"],
            "source_snapshot_sha256": first["source_snapshot_sha256"],
            "knowledge_cutoff": first["knowledge_cutoff"].isoformat(),
            "tepp_model_contract_version": first["tepp_model_contract_version"],
            "tepp_artifact_sha256": first["tepp_artifact_sha256"],
            "posterior_draw_set_id": first["posterior_draw_set_id"],
            "posterior_draw_count": int(first["posterior_draw_count"]),
            "topic_count": int(first["topic_count"]),
            "fast_mlsirm_version": first["fast_mlsirm_version"],
            "fast_mlsirm_code_revision": first["fast_mlsirm_code_revision"],
            "fast_mlsirm_artifact_sha256": first["fast_mlsirm_artifact_sha256"],
            "compute_backend_code": first["compute_backend_code"],
            "precision_code": first["precision_code"],
            "membership_fingerprint_sha256": first["membership_fingerprint_sha256"],
        },
        "topics": list(topics.values()),
    }


def _period_label(period_start: date | None, period_end: date | None) -> str:
    """Format the exact event-time interval represented by the projection."""
    if period_start and period_end:
        return f"{period_start.isoformat()} ~ {period_end.isoformat()} · 사건 발생일"
    if period_start:
        return f"{period_start.isoformat()} 이후 · 사건 발생일"
    if period_end:
        return f"{period_end.isoformat()} 이전 · 사건 발생일"
    return "전체 기간 · 사건 발생일"
