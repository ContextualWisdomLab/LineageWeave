"""ABAC-filtered projection of persisted operational case evidence."""

from __future__ import annotations

from datetime import date
import json
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
        pass  # pragma: no cover - structural Protocol member

    async def fetch(self, query: str, *args: object) -> list[Any]:
        """Fetch projected rows."""
        pass  # pragma: no cover - structural Protocol member


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
               fact.fact_ordinal
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
    topic_context = (
        {
            "status_code": "not_applicable",
            "reason_code": "external_information_view",
            "next_action": "전체 Dashboard로 전환해 Topic model influence를 확인하세요.",
            "required_contracts": [],
            "model_run": None,
            "topics": [],
        }
        if external_only
        else await _fetch_topic_context_dashboard(conn, visible, args)
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
        "topic_context": topic_context,
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
                "missing_facts": missing_facts.get((str(row["post_id"]), row["case_kind_code"]), []),
            }
            for row in case_rows
        ],
    }


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
            select post.post_id
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
                    where {authorized_model_scope}
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
                    where {authorized_model_scope}
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
                   membership.evidence_sha256 as membership_evidence_sha256,
                   membership.source_post_id, visible_post.occurred_at,
                   influence.influence_value,
                   influence.uncertainty_method_code,
                   influence.uncertainty_lower_value,
                   influence.uncertainty_upper_value,
                   influence.diagnostic_status_code,
                   influence_run.accepted_at
              from topic_post_context_influence influence
              join topic_influence_run influence_run
                on influence_run.topic_model_run_id = influence.topic_model_run_id
               and influence_run.topic_influence_run_id = influence.topic_influence_run_id
              join topic_model_run model
                on model.topic_model_run_id = influence.topic_model_run_id
              join analysis_run analysis on analysis.analysis_run_id = model.analysis_run_id
              join analysis_run_scope scope on scope.analysis_run_id = analysis.analysis_run_id
              join analysis_source_snapshot snapshot
                on snapshot.analysis_source_snapshot_id = analysis.analysis_source_snapshot_id
              join topic_context_membership membership
                on membership.topic_model_run_id = influence.topic_model_run_id
               and membership.topic_context_membership_id = influence.topic_context_membership_id
              join topic_context_definition context
                on context.topic_model_run_id = membership.topic_model_run_id
               and context.dimension_code = membership.dimension_code
               and context.context_id = membership.context_id
              join visible_post on visible_post.post_id = membership.source_post_id
              join topic_activity_interval activity
                on activity.topic_model_run_id = influence.topic_model_run_id
               and activity.topic_index = influence.topic_index
               and visible_post.occurred_at >= activity.valid_from
               and visible_post.occurred_at < activity.valid_to
             where visible_post.occurred_at >= membership.valid_from
               and visible_post.occurred_at < membership.valid_to
               and {authorized_model_scope}
        ), selected as (
            select topic_model_run_id, topic_influence_run_id
              from eligible
             order by accepted_at desc, topic_model_run_id, topic_influence_run_id
             limit 1
        )
        select eligible.*,
               coalesce((
                   select jsonb_agg(jsonb_build_object(
                              'event_code', relation.event_code,
                              'source_topic_index', relation.source_topic_index,
                              'target_topic_index', relation.target_topic_index,
                              'event_time', relation.event_time,
                              'evidence_sha256', relation.evidence_sha256
                          ) order by relation.event_time, relation.relation_ordinal)
                     from topic_lineage_relation relation
                    where relation.topic_model_run_id = eligible.topic_model_run_id
                      and (relation.source_topic_index = eligible.topic_index
                           or relation.target_topic_index = eligible.topic_index)
               ), '[]'::jsonb) as lineage_events
          from eligible
          join selected using (topic_model_run_id, topic_influence_run_id)
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
        return {
            "status_code": "unavailable",
            "reason_code": (
                "fast_mlsirm_influence_not_persisted"
                if tepp_ready
                else "tepp_topic_posterior_not_persisted"
            ),
            "next_action": (
                "동일 TEPP run·snapshot·cutoff에 결합된 fast-mlsirm 결과를 완료하세요."
                if tepp_ready
                else "TEPP posterior topic 계약 결과를 먼저 완료하세요."
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
                        if readiness and readiness["fast_mlsirm_influence_persisted"]
                        else "not_persisted"
                    ),
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
                "membership_evidence_sha256": row["membership_evidence_sha256"],
            }
        )

    return {
        "status_code": "accepted",
        "reason_code": None,
        "next_action": "Topic과 조직 수준을 선택해 model influence와 근거 글을 확인하세요.",
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
        return f"{period_start.isoformat()} ~ {period_end.isoformat()} · Event 발생일"
    if period_start:
        return f"{period_start.isoformat()} 이후 · Event 발생일"
    if period_end:
        return f"{period_end.isoformat()} 이전 · Event 발생일"
    return "전체 기간 · Event 발생일"
