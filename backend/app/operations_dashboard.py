"""ABAC-filtered projection of persisted operational case evidence."""

from __future__ import annotations

import base64
from datetime import date, datetime, time
import json
from typing import Any, Protocol
from uuid import UUID
from zoneinfo import ZoneInfo

from backend.app.post_eligibility import source_post_eligibility_sql
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
DASHBOARD_CASE_PAGE_SIZE = 20
DASHBOARD_CASE_PAGE_SIZE_MAX = 50


def _decode_case_cursor(raw: str | None) -> tuple[datetime, str, str] | None:
    """Decode and validate the last key of a Dashboard case page."""
    if not raw:
        return None
    try:
        padding = "=" * (-len(raw) % 4)
        payload = json.loads(base64.urlsafe_b64decode(raw + padding))
        occurred_at = datetime.fromisoformat(payload["occurred_at"])
        post_id = str(UUID(payload["post_id"]))
        case_kind_code = payload["case_kind_code"]
    except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
        raise ValueError("Resume from the last Dashboard case returned.") from exc
    if occurred_at.tzinfo is None or case_kind_code not in CASE_KIND_LABELS:
        raise ValueError("Resume from the last Dashboard case returned.")
    return occurred_at, post_id, case_kind_code


def _encode_case_cursor(row: Any) -> str:
    """Encode the stable sort key of one Dashboard case page."""
    payload = json.dumps(
        {
            "occurred_at": row["occurred_at"].isoformat(),
            "post_id": str(row["post_id"]),
            "case_kind_code": row["case_kind_code"],
        },
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return base64.urlsafe_b64encode(payload).decode("ascii").rstrip("=")


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


def _json_array(value: Any) -> list[dict[str, Any]]:
    """Normalize an asyncpg JSON array without changing its values."""
    decoded = json.loads(value) if isinstance(value, str) else value
    return [dict(row) for row in (decoded or [])]


class _DashboardBundleConnection:
    """Expose one database JSON bundle to the existing pure projection path."""

    def __init__(self, bundle: Any) -> None:
        self.metrics = dict(
            json.loads(bundle["metrics"])
            if isinstance(bundle["metrics"], str)
            else bundle["metrics"]
        )
        self.case_rollups = _json_array(bundle["case_rollups"])
        self.cases = _json_array(bundle["cases"])
        for row in self.cases:
            if isinstance(row["occurred_at"], str):
                row["occurred_at"] = datetime.fromisoformat(row["occurred_at"])
        self.details = _json_array(bundle["details"])
        self.topic_readiness = dict(
            json.loads(bundle["topic_readiness"])
            if isinstance(bundle["topic_readiness"], str)
            else bundle["topic_readiness"]
        )
        self.topic_readiness = {
            "tepp_posterior_persisted": self.topic_readiness.get("topic_tepp_ready"),
            "fast_mlsirm_influence_persisted": self.topic_readiness.get("topic_fast_ready"),
        }
        self.topic_details = _json_array(bundle["topic_details"])
        for row in self.topic_details:
            for key in (
                "occurred_at", "activity_valid_from", "activity_valid_to",
                "knowledge_cutoff", "accepted_at",
            ):
                if isinstance(row.get(key), str):
                    row[key] = datetime.fromisoformat(row[key])

    async def fetchrow(self, query: str, *args: object) -> Any:
        """Return the bundled scalar section selected by the projection."""
        if "tepp_posterior_persisted" in query:
            return self.topic_readiness
        return self.metrics

    async def fetch(self, query: str, *args: object) -> list[Any]:
        """Return the bundled row section selected by the projection."""
        if "dashboard_case_rollup" in query:
            return self.case_rollups
        if "select row_kind, payload" in query:
            return self.details
        if "from topic_post_context_influence influence" in query:
            return self.topic_details
        if "limit $9" in query:
            return self.cases
        return []

def _visible_scope_sql(
    alias: str = "post", *, source_context_required: bool | None = None
) -> str:
    """Return the shared ABAC and source-eligibility predicate."""
    return f"""
        ({alias}.visibility_code = 'public'
         or ({alias}.corporate_entity_id::text = any($1::text[])
             and (cardinality($2::text[]) = 0
                  or {alias}.process_unit_id::text = any($2::text[]))))
         and {source_post_eligibility_sql(alias, source_context_required=source_context_required)}
    """


def _visible_period_sql(
    alias: str = "post", *, source_context_required: bool | None = None
) -> str:
    """Return the shared visibility predicate plus the requested event interval."""
    return f"""
        {_visible_scope_sql(alias, source_context_required=source_context_required)}
        and ($3::date is null or (coalesce({alias}.event_occurred_at, {alias}.created_at)
             at time zone 'Asia/Seoul')::date >= $3)
        and ($4::date is null or (coalesce({alias}.event_occurred_at, {alias}.created_at)
             at time zone 'Asia/Seoul')::date <= $4)
    """


def _visible_projection_scope_sql(
    alias: str, *, source_context_required: bool | None
) -> str:
    """Return ABAC and eligibility over the maintained narrow read projection."""
    context = (
        ""
        if source_context_required is False
        else f"and {alias}.source_context_present"
        if source_context_required is True
        else f"""and ({alias}.source_context_present or not exists (
                    select 1 from dashboard_post_read_projection real_post
                     where real_post.active_source
                       and real_post.source_context_present
                       and (real_post.visibility_code = 'public'
                            or (real_post.corporate_entity_id = any($1::uuid[])
                                and (cardinality($2::uuid[]) = 0
                                     or real_post.process_unit_id = any($2::uuid[]))))
                ))"""
    )
    return f"""
        ({alias}.visibility_code = 'public'
         or ({alias}.corporate_entity_id = any($1::uuid[])
             and (cardinality($2::uuid[]) = 0
                  or {alias}.process_unit_id = any($2::uuid[]))))
        and {alias}.active_source {context}
    """


def _visible_projection_period_sql(
    alias: str, *, source_context_required: bool | None
) -> str:
    """Return projected ABAC and the requested event-date interval."""
    return f"""
        {_visible_projection_scope_sql(alias, source_context_required=source_context_required)}
        and ($3::date is null or {alias}.occurred_date >= $3)
        and ($4::date is null or {alias}.occurred_date <= $4)
    """


def _project_identity_lateral_sql(
    post_alias: str, post_id_column: str = "source_post_id"
) -> str:
    """Return exact source/semantic project keys separately from display names."""
    return f"""
        left join lateral (
            select array_agg(identity.project_key order by identity.project_name,
                                                       identity.project_key) as project_keys,
                   array_agg(identity.project_name order by identity.project_name,
                                                        identity.project_key) as project_key_labels,
                   array_agg(identity.key_provenance order by identity.project_name,
                                                            identity.project_key)
                       as project_key_provenances
              from (
                  select distinct on (
                             lower(btrim(normalize(candidate.project_key, NFKC),
                                         E' \t\n\r\f\v'))
                         )
                         candidate.project_key,
                         candidate.project_name,
                         candidate.key_provenance
                    from (
                        select nullif(btrim({post_alias}.source_project_code), '')
                                   as project_key,
                               coalesce(nullif(btrim({post_alias}.source_project_name), ''),
                                        nullif(btrim({post_alias}.source_project_code), ''))
                                   as project_name,
                               'source_post.source_project_code'::text as key_provenance,
                               0 as provenance_priority
                        union all
                        select nullif(btrim(key_mention.project_key), ''),
                               coalesce(nullif(btrim(key_mention.project_name), ''),
                                        nullif(btrim(key_mention.project_key), '')),
                               'post_project_mention.project_key'::text,
                               1
                          from post_project_mention key_mention
                         where key_mention.post_id = {post_alias}.{post_id_column}
                    ) candidate
                   where candidate.project_key is not null
                   order by lower(btrim(normalize(candidate.project_key, NFKC),
                                        E' \t\n\r\f\v')),
                            candidate.provenance_priority,
                            candidate.project_name,
                            candidate.project_key
              ) identity
        ) project_identity on true
    """


def _dashboard_single_statement_sql(source_context_required: bool | None) -> str:
    """Return the exact Dashboard read contract as one PostgreSQL statement."""
    visible = _visible_projection_period_sql(
        "post", source_context_required=source_context_required
    )
    evidence = _visible_projection_scope_sql(
        "evidence_post", source_context_required=source_context_required
    )
    milestone_evidence = _visible_projection_scope_sql(
        "milestone_evidence", source_context_required=source_context_required
    )
    contributor_evidence = _visible_projection_scope_sql(
        "contributor_evidence", source_context_required=source_context_required
    )
    summary_context = (
        "summary.source_context_present"
        if source_context_required is True
        else "true"
        if source_context_required is False
        else """(summary.source_context_present or not exists (
                    select 1 from dashboard_post_read_projection real_post
                     where real_post.active_source
                       and real_post.source_context_present
                       and (real_post.visibility_code = 'public'
                            or (real_post.corporate_entity_id = any($1::uuid[])
                                and (cardinality($2::uuid[]) = 0
                                     or real_post.process_unit_id = any($2::uuid[]))))
                ))"""
    )
    return f"""
    /* dashboard_single_statement */
    with visible_post as not materialized (
        select post.*
          from dashboard_post_read_projection post
         where {visible}
    ), external_post as materialized (
        select classification.post_id,
               bool_or(not visible_post.case_analysis_present
                       and not visible_post.ingestion_failed) as pending_analysis,
               bool_or(visible_post.ingestion_failed) as failed_analysis
          from operations_case_classification classification
          join visible_post on visible_post.source_post_id = classification.post_id
          join dashboard_post_read_projection evidence_post
            on evidence_post.source_post_id = classification.evidence_post_id
         where {evidence}
           and classification.case_kind_code = 'external_information'
         group by classification.post_id
    ), summary_metric as (
        select coalesce(sum(summary.total_post_count), 0) as total_post_count,
               coalesce(sum(summary.pending_analysis_count), 0)
                   as pending_analysis_count,
               coalesce(sum(summary.failed_analysis_count), 0)
                   as failed_analysis_count
          from dashboard_post_daily_summary summary
         where (summary.visibility_code = 'public'
                or (summary.corporate_entity_id = any($1::uuid[])
                    and (cardinality($2::uuid[]) = 0
                         or summary.process_unit_id = any($2::uuid[]))))
           and ($3::date is null or summary.occurred_date >= $3)
           and ($4::date is null or summary.occurred_date <= $4)
           and ({summary_context})
    ), metric as (
        select summary_metric.total_post_count,
               (select count(*) from external_post) as external_post_count,
               case when $5::boolean
                    then (select count(*) from external_post where pending_analysis)
                    else summary_metric.pending_analysis_count end
                   as pending_analysis_count,
               case when $5::boolean
                    then (select count(*) from external_post where failed_analysis)
                    else summary_metric.failed_analysis_count end
                   as failed_analysis_count
          from summary_metric
    ), case_rollup as materialized (
        select rollup.source_post_id as post_id, rollup.case_kind_code,
               coalesce(milestone.event_count, 0) as event_count,
               coalesce(milestone.claim_started, false) as claim_started,
               coalesce(milestone.claim_ended, false) as claim_ended,
               coalesce(milestone.rebid_started, false) as rebid_started,
               coalesce(milestone.rebid_ended, false) as rebid_ended,
               coalesce(milestone.handover_started, false) as handover_started,
               coalesce(milestone.handover_ended, false) as handover_ended,
               rollup.claim_start_missing, rollup.rebid_start_missing,
               rollup.handover_start_missing
          from dashboard_case_rollup_read_projection rollup
          join visible_post post on post.source_post_id = rollup.source_post_id
          join dashboard_post_read_projection evidence_post
            on evidence_post.source_post_id = rollup.classification_evidence_post_id
          left join lateral (
              select sum(value.event_count) as event_count,
                     bool_or(value.claim_started) as claim_started,
                     bool_or(value.claim_ended) as claim_ended,
                     bool_or(value.rebid_started) as rebid_started,
                     bool_or(value.rebid_ended) as rebid_ended,
                     bool_or(value.handover_started) as handover_started,
                     bool_or(value.handover_ended) as handover_ended
                from dashboard_case_milestone_read_projection value
                join dashboard_post_read_projection milestone_evidence
                  on milestone_evidence.source_post_id = value.evidence_post_id
               where value.source_post_id = rollup.source_post_id
                 and value.case_kind_code = rollup.case_kind_code
                 and {milestone_evidence}
          ) milestone on true
         where {evidence}
           and not exists (
               select 1
                 from dashboard_case_contributor_read_projection contributor
                 left join dashboard_post_read_projection contributor_evidence
                   on contributor_evidence.source_post_id = contributor.evidence_post_id
                where contributor.source_post_id = rollup.source_post_id
                  and contributor.case_kind_code = rollup.case_kind_code
                  and (contributor_evidence.source_post_id is null
                       or not ({contributor_evidence}))
           )
           and ($5::boolean is false or rollup.case_kind_code = 'external_information')
    ), case_ranked as materialized (
        select rollup.source_post_id as post_id, rollup.case_kind_code,
               rollup.summary_text, rollup.evidence_text,
               rollup.classification_evidence_post_id as evidence_post_id,
               rollup.occurred_at, rollup.project_name, rollup.project_names,
               coalesce(project_identity.project_keys, array[]::text[]) as project_keys,
               coalesce(project_identity.project_key_labels, array[]::text[])
                   as project_key_labels,
               coalesce(project_identity.project_key_provenances, array[]::text[])
                   as project_key_provenances
          from dashboard_case_rollup_read_projection rollup
          join visible_post post on post.source_post_id = rollup.source_post_id
          join dashboard_post_read_projection evidence_post
            on evidence_post.source_post_id = rollup.classification_evidence_post_id
          {_project_identity_lateral_sql('post')}
         where {evidence}
           and not exists (
               select 1
                 from dashboard_case_contributor_read_projection contributor
                 left join dashboard_post_read_projection contributor_evidence
                   on contributor_evidence.source_post_id = contributor.evidence_post_id
                where contributor.source_post_id = rollup.source_post_id
                  and contributor.case_kind_code = rollup.case_kind_code
                  and (contributor_evidence.source_post_id is null
                       or not ({contributor_evidence}))
           )
           and ($5::boolean is false or rollup.case_kind_code = 'external_information')
           and ($6::timestamptz is null
                or (rollup.occurred_at,
                    rollup.source_post_id, rollup.case_kind_code)
                   < ($6, $7::uuid, $8::text))
         order by rollup.occurred_at desc, rollup.source_post_id desc,
                  rollup.case_kind_code desc
         limit $9 + 1
    ), case_summary as materialized (
        select case_kind_code,
               count(*) as post_count,
               coalesce(sum(event_count), 0) as event_count,
               count(*) filter (where claim_started and claim_ended
                                      and not claim_start_missing) as claim_resolved,
               count(*) filter (where claim_started and not claim_ended
                                      and not claim_start_missing) as claim_open,
               count(*) filter (where not claim_started or claim_start_missing)
                   as claim_missing,
               count(*) filter (where rebid_started and rebid_ended
                                      and not rebid_start_missing) as rebid_resolved,
               count(*) filter (where rebid_started and not rebid_ended
                                      and not rebid_start_missing) as rebid_open,
               count(*) filter (where not rebid_started or rebid_start_missing)
                   as rebid_missing,
               count(*) filter (where handover_started and handover_ended
                                      and not handover_start_missing) as handover_resolved,
               count(*) filter (where handover_started and not handover_ended
                                      and not handover_start_missing) as handover_open,
               count(*) filter (where not handover_started or handover_start_missing)
                   as handover_missing
          from case_rollup
         group by case_kind_code
    ), selected_case as materialized (
        select post_id, case_kind_code
          from case_ranked
         order by occurred_at desc, post_id desc, case_kind_code desc
         limit $9
    ), detail as materialized (
        select 'fact'::text as row_kind, fact.post_id, fact.case_kind_code,
               fact.fact_ordinal::bigint as sort_ordinal,
               jsonb_build_object(
                   'post_id', fact.post_id, 'case_kind_code', fact.case_kind_code,
                   'fact_type_code', fact.fact_type_code, 'value_text', fact.value_text,
                   'evidence_text', fact.evidence_text,
                   'evidence_post_id', fact.evidence_post_id,
                   'fact_ordinal', fact.fact_ordinal,
                   'relation_target_kind_code', fact.relation_target_kind_code
               ) as payload
          from selected_case selected
          join operations_case_fact fact using (post_id, case_kind_code)
          join dashboard_post_read_projection evidence_post
            on evidence_post.source_post_id = fact.evidence_post_id
         where {evidence}
        union all
        select 'product', relation.post_id, relation.case_kind_code,
               relation.fact_ordinal::bigint,
               jsonb_build_object(
                   'post_id', relation.post_id, 'case_kind_code', relation.case_kind_code,
                   'fact_ordinal', relation.fact_ordinal,
                   'relation_type_code', relation.relation_type_code,
                   'extracted_product_name', mention.extracted_product_name,
                   'canonical_product_name', catalog.canonical_product_name,
                   'evidence_text', relation.evidence_text,
                   'evidence_post_id', relation.evidence_post_id
               )
          from selected_case selected
          join product_operations_fact_relation relation using (post_id, case_kind_code)
          join post_product_analysis product_analysis
            on product_analysis.post_id = relation.post_id
           and product_analysis.orchestrator_model_receipt is not null
          join post_content_ingestion_job product_job
            on product_job.post_id = relation.post_id
           and product_job.source_body_sha256 = product_analysis.source_body_sha256
          join post_product_mention mention
            on mention.post_id = relation.post_id
           and mention.mention_ordinal = relation.mention_ordinal
          left join product_catalog catalog
            on catalog.product_catalog_id = mention.product_catalog_id
          join dashboard_post_read_projection evidence_post
            on evidence_post.source_post_id = relation.evidence_post_id
         where {evidence}
        union all
        select 'missing_fact', missing.post_id, missing.case_kind_code, 0,
               jsonb_build_object(
                   'post_id', missing.post_id, 'case_kind_code', missing.case_kind_code,
                   'fact_type_code', missing.fact_type_code
               )
          from selected_case selected
          join operations_case_missing_fact missing using (post_id, case_kind_code)
        union all
        select 'missing_fact', fact.post_id, fact.case_kind_code,
               fact.fact_ordinal::bigint,
               jsonb_build_object(
                   'post_id', fact.post_id, 'case_kind_code', fact.case_kind_code,
                   'fact_type_code', fact.fact_type_code
               )
          from selected_case selected
          join operations_case_fact fact using (post_id, case_kind_code)
          left join dashboard_post_read_projection evidence_post
            on evidence_post.source_post_id = fact.evidence_post_id
         where (evidence_post.source_post_id is null or not ({evidence}))
           and ($10::jsonb -> fact.case_kind_code) ? fact.fact_type_code
        union all
        select 'milestone', milestone.post_id, milestone.case_kind_code,
               (extract(epoch from milestone.observed_at) * 1000000)::bigint,
               jsonb_build_object(
                   'post_id', milestone.post_id,
                   'case_kind_code', milestone.case_kind_code,
                   'milestone_type_code', milestone.milestone_type_code,
                   'evidence_text', milestone.evidence_text,
                   'evidence_post_id', milestone.evidence_post_id,
                   'observed_at', milestone.observed_at,
                   'time_axis_code', milestone.time_axis_code,
                   'is_missing', false
               )
          from selected_case selected
          join operations_case_milestone milestone using (post_id, case_kind_code)
          join dashboard_post_read_projection evidence_post
            on evidence_post.source_post_id = milestone.evidence_post_id
         where {evidence}
        union all
        select 'milestone', missing.post_id, missing.case_kind_code,
               9223372036854775807,
               jsonb_build_object(
                   'post_id', missing.post_id,
                   'case_kind_code', missing.case_kind_code,
                   'milestone_type_code', missing.milestone_type_code,
                   'evidence_text', null, 'evidence_post_id', null,
                   'observed_at', null, 'time_axis_code', null,
                   'is_missing', true
               )
          from selected_case selected
          join operations_case_missing_milestone missing using (post_id, case_kind_code)
    ), topic_candidate as materialized (
        select model.topic_model_run_id, influence_run.topic_influence_run_id,
               model.tepp_run_id, model.tepp_snapshot_id,
               model.tepp_schema_version, model.tepp_model_contract_version,
               model.tepp_artifact_sha256, model.posterior_draw_set_id,
               model.posterior_draw_count, model.topic_count,
               snapshot.snapshot_sha256 as source_snapshot_sha256,
               analysis.knowledge_cutoff,
               influence_run.fast_mlsirm_schema_version,
               influence_run.fast_mlsirm_version,
               influence_run.fast_mlsirm_code_revision,
               influence_run.fast_mlsirm_artifact_sha256,
               influence_run.compute_backend_code, influence_run.precision_code,
               influence_run.membership_fingerprint_sha256
          from topic_model_run model
          join analysis_run analysis on analysis.analysis_run_id = model.analysis_run_id
          join analysis_source_snapshot snapshot
            on snapshot.analysis_source_snapshot_id = analysis.analysis_source_snapshot_id
          join analysis_run_scope scope on scope.analysis_run_id = analysis.analysis_run_id
          join topic_influence_run influence_run
            on influence_run.topic_model_run_id = model.topic_model_run_id
         where $5::boolean is false
           and ((scope.scope_kind_code = 'analysis_scope_corporate_entity'
                 and scope.corporate_entity_id = any($1::uuid[])
                 and cardinality($2::uuid[]) = 0)
                or (scope.scope_kind_code = 'analysis_scope_process_unit'
                    and scope.process_unit_id = any($2::uuid[])))
         order by influence_run.accepted_at desc, model.topic_model_run_id,
                  influence_run.topic_influence_run_id
         limit 1
    ), topic_detail as materialized (
        select influence.*, membership.dimension_code, membership.context_id,
               context.context_label, membership.membership_weight,
               membership.source_post_id,
               evidence_binding.node_id as membership_evidence_post_id,
               post.occurred_at,
               activity.state_code, activity.valid_from as activity_valid_from,
               activity.valid_to as activity_valid_to,
               candidate.*,
               evidence_post.source_post_id is not null
               and not exists (
                   select 1
                     from topic_lineage_relation checked_relation
                     left join provenance_assertion checked_assertion
                       on checked_assertion.assertion_id = checked_relation.provenance_assertion_id
                     left join provenance_resource_binding checked_binding
                       on checked_binding.resource_id = checked_assertion.object_resource_id
                      and checked_binding.node_type_code = 'node_post'
                     left join visible_post checked_visible
                       on checked_visible.source_post_id = checked_binding.node_id
                    where checked_relation.topic_model_run_id = candidate.topic_model_run_id
                      and checked_visible.source_post_id is null
               ) as provenance_complete,
               coalesce((
                   select jsonb_agg(jsonb_build_object(
                              'event_code', relation.event_code,
                              'source_topic_index', relation.source_topic_index,
                              'target_topic_index', relation.target_topic_index,
                              'event_time', relation.event_time,
                              'evidence_post_id', relation_binding.node_id
                          ) order by relation.event_time, relation.relation_ordinal)
                     from topic_lineage_relation relation
                     join provenance_assertion relation_assertion
                       on relation_assertion.assertion_id = relation.provenance_assertion_id
                     join provenance_resource_binding relation_binding
                       on relation_binding.resource_id = relation_assertion.object_resource_id
                      and relation_binding.node_type_code = 'node_post'
                     join visible_post relation_visible
                       on relation_visible.source_post_id = relation_binding.node_id
                    where relation.topic_model_run_id = candidate.topic_model_run_id
                      and (relation.source_topic_index = influence.topic_index
                           or relation.target_topic_index = influence.topic_index)
               ), '[]'::jsonb) as lineage_events
          from topic_candidate candidate
          join topic_post_context_influence influence
            on influence.topic_model_run_id = candidate.topic_model_run_id
           and influence.topic_influence_run_id = candidate.topic_influence_run_id
          join topic_context_membership membership
            on membership.topic_model_run_id = influence.topic_model_run_id
           and membership.topic_context_membership_id = influence.topic_context_membership_id
          join topic_context_definition context
            on context.topic_model_run_id = membership.topic_model_run_id
           and context.dimension_code = membership.dimension_code
           and context.context_id = membership.context_id
          join visible_post post on post.source_post_id = membership.source_post_id
          join topic_activity_interval activity
            on activity.topic_model_run_id = influence.topic_model_run_id
           and activity.topic_index = influence.topic_index
           and post.occurred_at >= activity.valid_from
           and post.occurred_at < activity.valid_to
           and post.occurred_at >= membership.valid_from
           and post.occurred_at < membership.valid_to
          left join provenance_assertion membership_assertion
            on membership_assertion.assertion_id = membership.provenance_assertion_id
          left join provenance_resource_binding evidence_binding
            on evidence_binding.resource_id = membership_assertion.object_resource_id
           and evidence_binding.node_type_code = 'node_post'
          left join dashboard_post_read_projection evidence_post
            on evidence_post.source_post_id = evidence_binding.node_id
           and {evidence}
    )
    select row_to_json(metric) as metrics,
           coalesce((select json_agg(row_to_json(case_summary)
                                     order by case_kind_code)
                       from case_summary), '[]'::json) as case_rollups,
           coalesce((select json_agg(row_to_json(case_ranked)
                                     order by occurred_at desc, post_id desc,
                                              case_kind_code desc)
                       from case_ranked), '[]'::json) as cases,
           coalesce((select json_agg(json_build_object(
                                'row_kind', row_kind, 'payload', payload)
                                     order by post_id, case_kind_code,
                                              sort_ordinal, row_kind)
                       from detail), '[]'::json) as details,
           json_build_object(
               'topic_tepp_ready', exists(
                   select 1 from topic_context_membership membership
                   join visible_post on visible_post.source_post_id = membership.source_post_id
                     and visible_post.occurred_at >= membership.valid_from
                     and visible_post.occurred_at < membership.valid_to
               ),
               'topic_fast_ready', exists(select 1 from topic_detail)
           ) as topic_readiness,
           coalesce((select json_agg(row_to_json(topic_detail)
                                     order by topic_index, dimension_code,
                                              context_label, influence_value desc,
                                              occurred_at, source_post_id)
                       from topic_detail), '[]'::json) as topic_details
      from metric
    """


async def fetch_operations_dashboard(
    conn: _Connection,
    corporate_entity_ids: tuple[str, ...] | list[str],
    process_unit_ids: tuple[str, ...] | list[str] = (),
    period_start: date | None = None,
    period_end: date | None = None,
    external_only: bool = False,
    source_context_required: bool | None = None,
    case_cursor: str | None = None,
    case_limit: int = DASHBOARD_CASE_PAGE_SIZE,
) -> dict[str, Any]:
    """Return quantified cases and their persisted source evidence."""
    if period_start and period_end and period_start > period_end:
        raise ValueError("period_start must not be after period_end")
    if case_limit < 1 or case_limit > DASHBOARD_CASE_PAGE_SIZE_MAX:
        raise ValueError(
            f"Request between 1 and {DASHBOARD_CASE_PAGE_SIZE_MAX} Dashboard cases."
        )
    cursor = _decode_case_cursor(case_cursor)
    source_args = (
        list(corporate_entity_ids), list(process_unit_ids),
        period_start, period_end, external_only,
    )
    args = (
        [UUID(value) for value in corporate_entity_ids],
        [UUID(value) for value in process_unit_ids],
        period_start, period_end, external_only,
    )
    cursor_args = cursor or (None, None, None)
    bundle = await conn.fetchrow(
        _dashboard_single_statement_sql(source_context_required),
        *args,
        *cursor_args,
        case_limit,
        json.dumps(
            {
                case_kind: sorted(fact_types)
                for case_kind, fact_types in REQUIRED_FACT_TYPES.items()
            }
        ),
    )
    conn = _DashboardBundleConnection(bundle)
    visible = _visible_period_sql(source_context_required=source_context_required)
    projected_visible = _visible_projection_period_sql(
        "post", source_context_required=source_context_required
    )
    projected_evidence = _visible_projection_scope_sql(
        "evidence_post", source_context_required=source_context_required
    )
    metrics = await conn.fetchrow(
        f"""
        with visible_post as materialized (
            select post.source_post_id as post_id,
                   post.case_analysis_present, post.ingestion_failed
              from dashboard_post_read_projection post
             where {projected_visible}
        ), external_post as (
            select distinct classification.post_id
              from operations_case_classification classification
              join visible_post on visible_post.post_id = classification.post_id
              join dashboard_post_read_projection evidence_post
                on evidence_post.source_post_id = classification.evidence_post_id
             where {projected_evidence}
               and classification.case_kind_code = 'external_information'
        )
        select count(*) as total_post_count,
               count(external_post.post_id) as external_post_count,
               count(*) filter (
                   where ($5::boolean is false or external_post.post_id is not null)
                     and not visible_post.case_analysis_present
                     and not visible_post.ingestion_failed
               ) as pending_analysis_count,
               count(*) filter (
                   where ($5::boolean is false or external_post.post_id is not null)
                     and visible_post.ingestion_failed
               ) as failed_analysis_count
          from visible_post
          left join external_post using (post_id)
        """,
        *args,
    )
    case_rollup_rows = await conn.fetch(
        f"""
        /* dashboard_case_rollup */
        select rollup.source_post_id as post_id, rollup.case_kind_code,
               coalesce(milestone.event_count, 0) as event_count,
               coalesce(milestone.claim_started, false) as claim_started,
               coalesce(milestone.claim_ended, false) as claim_ended,
               coalesce(milestone.rebid_started, false) as rebid_started,
               coalesce(milestone.rebid_ended, false) as rebid_ended,
               coalesce(milestone.handover_started, false) as handover_started,
               coalesce(milestone.handover_ended, false) as handover_ended,
               rollup.claim_start_missing, rollup.rebid_start_missing,
               rollup.handover_start_missing
          from dashboard_case_rollup_read_projection rollup
          join dashboard_post_read_projection post
            on post.source_post_id = rollup.source_post_id
          join dashboard_post_read_projection evidence_post
            on evidence_post.source_post_id = rollup.classification_evidence_post_id
          left join lateral (
              select sum(value.event_count) as event_count,
                     bool_or(value.claim_started) as claim_started,
                     bool_or(value.claim_ended) as claim_ended,
                     bool_or(value.rebid_started) as rebid_started,
                     bool_or(value.rebid_ended) as rebid_ended,
                     bool_or(value.handover_started) as handover_started,
                     bool_or(value.handover_ended) as handover_ended
                from dashboard_case_milestone_read_projection value
                join dashboard_post_read_projection milestone_evidence
                  on milestone_evidence.source_post_id = value.evidence_post_id
               where value.source_post_id = rollup.source_post_id
                 and value.case_kind_code = rollup.case_kind_code
                 and {_visible_projection_scope_sql('milestone_evidence', source_context_required=source_context_required)}
          ) milestone on true
         where {projected_visible}
           and {projected_evidence}
           and ($5::boolean is false
                or rollup.case_kind_code = 'external_information')
        """,
        *args,
    )
    case_rows = await conn.fetch(
        f"""
        select classification.post_id, classification.case_kind_code,
               classification.summary_text, classification.evidence_text,
               classification.evidence_post_id,
               coalesce(post.event_occurred_at, post.created_at) as occurred_at,
               coalesce(nullif(btrim(post.source_project_name), ''), project.primary_project_name,
                        nullif(btrim(post.source_project_code), ''))
                   as project_name,
               coalesce(project.project_names, array[]::text[]) as project_names,
               coalesce(project_identity.project_keys, array[]::text[]) as project_keys,
               coalesce(project_identity.project_key_labels, array[]::text[]) as project_key_labels,
               coalesce(project_identity.project_key_provenances, array[]::text[])
                   as project_key_provenances
          from operations_case_classification classification
          join dashboard_post_read_projection post_scope
            on post_scope.source_post_id = classification.post_id
          join source_post post on post.post_id = post_scope.source_post_id
          join dashboard_post_read_projection evidence_post
            on evidence_post.source_post_id = classification.evidence_post_id
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
                    select coalesce(nullif(btrim(post.source_project_name), ''),
                                    nullif(btrim(post.source_project_code), '')) as project_name
                    union
                    select nullif(btrim(mention.project_name), '')
                      from post_project_mention mention
                     where mention.post_id = post.post_id
                ) names
               where names.project_name is not null
          ) project on true
          {_project_identity_lateral_sql('post', 'post_id')}
             where {_visible_projection_period_sql('post_scope', source_context_required=source_context_required)}
               and {projected_evidence}
               and ($5::boolean is false or classification.case_kind_code = 'external_information')
               and ($6::timestamptz is null
                    or (coalesce(post.event_occurred_at, post.created_at),
                        classification.post_id, classification.case_kind_code)
                       < ($6, $7::uuid, $8::text))
         order by coalesce(post.event_occurred_at, post.created_at) desc,
                  classification.post_id desc, classification.case_kind_code desc
         limit $9
        """,
        *args,
        *cursor_args,
        case_limit + 1,
    )
    has_more_cases = len(case_rows) > case_limit
    if has_more_cases:
        case_rows = case_rows[:case_limit]
    next_case_cursor = _encode_case_cursor(case_rows[-1]) if has_more_cases else None
    selected_post_ids = [str(row["post_id"]) for row in case_rows]
    selected_case_kinds = [row["case_kind_code"] for row in case_rows]
    selected_args = (args[0], args[1], selected_post_ids, selected_case_kinds)
    detail_bundle_rows = await conn.fetch(
        f"""
        with selected_case as (
            select * from unnest($3::uuid[], $4::text[])
                as selected(post_id, case_kind_code)
        ), detail as (
        select 'fact'::text as row_kind,
               jsonb_build_object(
                   'post_id', fact.post_id, 'case_kind_code', fact.case_kind_code,
                   'fact_type_code', fact.fact_type_code, 'value_text', fact.value_text,
                   'evidence_text', fact.evidence_text,
                   'evidence_post_id', fact.evidence_post_id,
                   'fact_ordinal', fact.fact_ordinal,
                   'relation_target_kind_code', fact.relation_target_kind_code
               ) as payload,
               fact.post_id as sort_post_id, fact.case_kind_code as sort_case_kind,
               fact.fact_ordinal::bigint as sort_ordinal
          from selected_case selected
          join operations_case_fact fact using (post_id, case_kind_code)
          join dashboard_post_read_projection evidence_post
            on evidence_post.source_post_id = fact.evidence_post_id
         where {projected_evidence}
        union all
        select 'product',
               jsonb_build_object(
                   'post_id', relation.post_id, 'case_kind_code', relation.case_kind_code,
                   'fact_ordinal', relation.fact_ordinal,
                   'relation_type_code', relation.relation_type_code,
                   'extracted_product_name', mention.extracted_product_name,
                   'canonical_product_name', catalog.canonical_product_name,
                   'evidence_text', relation.evidence_text,
                   'evidence_post_id', relation.evidence_post_id
               ), relation.post_id, relation.case_kind_code,
               relation.fact_ordinal::bigint
          from selected_case selected
          join product_operations_fact_relation relation using (post_id, case_kind_code)
          join post_product_analysis product_analysis
            on product_analysis.post_id = relation.post_id
           and product_analysis.orchestrator_model_receipt is not null
          join post_content_ingestion_job product_job
            on product_job.post_id = relation.post_id
           and product_job.source_body_sha256 = product_analysis.source_body_sha256
          join post_product_mention mention
            on mention.post_id = relation.post_id
           and mention.mention_ordinal = relation.mention_ordinal
          left join product_catalog catalog
            on catalog.product_catalog_id = mention.product_catalog_id
          join dashboard_post_read_projection evidence_post
            on evidence_post.source_post_id = relation.evidence_post_id
         where {projected_evidence}
        union all
        select 'missing_fact',
               jsonb_build_object(
                   'post_id', missing.post_id, 'case_kind_code', missing.case_kind_code,
                   'fact_type_code', missing.fact_type_code
               ), missing.post_id, missing.case_kind_code, 0
          from selected_case selected
          join operations_case_missing_fact missing using (post_id, case_kind_code)
        union all
        select 'missing_fact',
               jsonb_build_object(
                   'post_id', fact.post_id, 'case_kind_code', fact.case_kind_code,
                   'fact_type_code', fact.fact_type_code
               ), fact.post_id, fact.case_kind_code, fact.fact_ordinal::bigint
          from selected_case selected
          join operations_case_fact fact using (post_id, case_kind_code)
          left join dashboard_post_read_projection evidence_post
            on evidence_post.source_post_id = fact.evidence_post_id
         where (evidence_post.source_post_id is null or not ({projected_evidence}))
           and ($5::jsonb -> fact.case_kind_code) ? fact.fact_type_code
        union all
        select 'milestone',
               jsonb_build_object(
                   'post_id', milestone.post_id,
                   'case_kind_code', milestone.case_kind_code,
                   'milestone_type_code', milestone.milestone_type_code,
                   'evidence_text', milestone.evidence_text,
                   'evidence_post_id', milestone.evidence_post_id,
                   'observed_at', milestone.observed_at,
                   'time_axis_code', milestone.time_axis_code,
                   'is_missing', false
               ), milestone.post_id, milestone.case_kind_code,
               (extract(epoch from milestone.observed_at) * 1000000)::bigint
          from selected_case selected
          join operations_case_milestone milestone using (post_id, case_kind_code)
          join dashboard_post_read_projection evidence_post
            on evidence_post.source_post_id = milestone.evidence_post_id
         where {projected_evidence}
        union all
        select 'milestone',
               jsonb_build_object(
                   'post_id', missing.post_id,
                   'case_kind_code', missing.case_kind_code,
                   'milestone_type_code', missing.milestone_type_code,
                   'evidence_text', null, 'evidence_post_id', null,
                   'observed_at', null, 'time_axis_code', null,
                   'is_missing', true
               ), missing.post_id, missing.case_kind_code, 9223372036854775807
          from selected_case selected
          join operations_case_missing_milestone missing using (post_id, case_kind_code)
        )
        select row_kind, payload
          from detail
         order by sort_post_id, sort_case_kind, sort_ordinal, row_kind
        """,
        *selected_args,
        json.dumps(
            {
                case_kind: sorted(fact_types)
                for case_kind, fact_types in REQUIRED_FACT_TYPES.items()
            }
        ),
    )
    fact_rows: list[dict[str, Any]] = []
    product_relation_rows: list[dict[str, Any]] = []
    missing_rows: list[dict[str, Any]] = []
    milestone_rows: list[dict[str, Any]] = []
    detail_targets = {
        "fact": fact_rows,
        "product": product_relation_rows,
        "missing_fact": missing_rows,
        "milestone": milestone_rows,
    }
    for bundle_row in detail_bundle_rows:
        payload = bundle_row["payload"]
        detail_targets[bundle_row["row_kind"]].append(
            json.loads(payload) if isinstance(payload, str) else dict(payload)
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
        else await _fetch_topic_context_dashboard(conn, visible, source_args[:4])
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
        observed_at = row["observed_at"]
        milestones.setdefault(key, []).append(
            {
                "milestone_type_code": row["milestone_type_code"],
                "milestone_type_label": MILESTONE_TYPE_LABELS[
                    row["milestone_type_code"]
                ],
                "evidence_text": row["evidence_text"],
                "evidence_post_id": str(row["evidence_post_id"]),
                "observed_at": (
                    observed_at if isinstance(observed_at, str) else observed_at.isoformat()
                ),
                "time_axis_code": row["time_axis_code"],
                "time_axis_label": (
                    "사건 발생일"
                    if row["time_axis_code"] == "event_occurred_at"
                    else "기록 생성일"
                ),
            }
        )
    total = int(metrics["total_post_count"])
    case_post_counts: dict[str, int] = {}
    case_event_counts: dict[str, int] = {}
    for row in case_rollup_rows:
        kind = row["case_kind_code"]
        case_post_counts[kind] = case_post_counts.get(kind, 0) + int(
            row.get("post_count", 1)
        )
        case_event_counts[kind] = case_event_counts.get(kind, 0) + int(
            row["event_count"]
        )
    external = int(metrics["external_post_count"])
    pending_analysis_count = int(metrics["pending_analysis_count"])
    failed_analysis_count = int(metrics["failed_analysis_count"])
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
    for row in case_rollup_rows:
        for lifecycle_code, required_kind, _label, start_code, end_code in LIFECYCLE_DEFINITIONS:
            if row["case_kind_code"] != required_kind:
                continue
            prefix = lifecycle_code.removesuffix("_investigation").removesuffix("_response").removesuffix("_gap")
            if f"{prefix}_resolved" in row:
                lifecycle_metrics[lifecycle_code]["resolved_case_count"] += int(
                    row[f"{prefix}_resolved"]
                )
                lifecycle_metrics[lifecycle_code]["open_case_count"] += int(
                    row[f"{prefix}_open"]
                )
                lifecycle_metrics[lifecycle_code]["evidence_missing_case_count"] += int(
                    row[f"{prefix}_missing"]
                )
                continue
            started = bool(row[f"{prefix}_started"])
            ended = bool(row[f"{prefix}_ended"])
            start_missing = bool(row[f"{prefix}_start_missing"])
            status_code = "resolved" if started and ended else "open" if started else "evidence_missing"
            if start_missing:
                status_code = "evidence_missing"
            lifecycle_metrics[lifecycle_code][f"{status_code}_case_count"] += 1
    for row in case_rows:
        key = (str(row["post_id"]), row["case_kind_code"])
        case_milestones = milestones.get(key, [])
        case_lifecycles = _project_lifecycles(
            row["case_kind_code"], case_milestones, missing_milestones.get(key, set())
        )
        projected_cases.append(
            {
                "post_id": str(row["post_id"]),
                "case_kind_code": row["case_kind_code"],
                "case_kind_label": CASE_KIND_LABELS[row["case_kind_code"]],
                "project_name": row["project_name"],
                "project_names": list(row["project_names"]),
                "projects": [
                    {
                        "project_key": project_key,
                        "project_name": project_name,
                        "key_provenance": key_provenance,
                        "evidence_post_id": str(row["post_id"]),
                    }
                    for project_key, project_name, key_provenance in zip(
                        row["project_keys"],
                        row["project_key_labels"],
                        row["project_key_provenances"],
                        strict=True,
                    )
                ],
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
        "period_start": period_start.isoformat() if period_start else None,
        "period_end": period_end.isoformat() if period_end else None,
        "project_history_knowledge_cutoff": (
            (
                datetime.combine(period_end, time.max, tzinfo=ZoneInfo("Asia/Seoul"))
            ).isoformat()
            if period_end
            else None
        ),
        "period_time_axis_code": "event_occurred_at",
        "total_post_count": total,
        "total_event_count": sum(case_event_counts.values()),
        "external_post_count": external,
        "external_percent": external * 100 / total if total else 0.0,
        "pending_analysis_count": pending_analysis_count,
        "failed_analysis_count": failed_analysis_count,
        "case_metrics": [
            {
                "case_kind_code": kind,
                "case_kind_label": label,
                "event_count": case_event_counts.get(kind, 0),
                "post_count": case_post_counts.get(kind, 0),
            }
            for kind, label in CASE_KIND_LABELS.items()
        ],
        "topic_context": topic_context,
        "lifecycle_metrics": list(lifecycle_metrics.values()),
        "cases": projected_cases,
        "next_case_cursor": next_case_cursor,
    }


async def warm_operations_dashboard_read_statements(conn: _Connection) -> None:
    """Prepare the bounded Dashboard query shapes before serving requests."""
    required_facts = json.dumps(
        {
            case_kind: sorted(fact_types)
            for case_kind, fact_types in REQUIRED_FACT_TYPES.items()
        }
    )
    for source_context_required in (None, True, False):
        await conn.fetchrow(
            _dashboard_single_statement_sql(source_context_required),
            [], [], None, None, False, None, None, None, 20, required_facts,
        )


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


def _unavailable_topic_context(tepp_ready: bool) -> dict[str, Any]:
    """Return the existing fail-closed topic-context state."""
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
                "state_code": "not_persisted",
            },
        ],
        "model_run": None,
        "topics": [],
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
    tepp_ready = bool(readiness and readiness["tepp_posterior_persisted"])
    fast_mlsirm_ready = bool(
        readiness and readiness["fast_mlsirm_influence_persisted"]
    )
    if not tepp_ready or not fast_mlsirm_ready:
        return _unavailable_topic_context(tepp_ready)

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
        # The readiness query can see an accepted influence row from a
        # different selected run than the projection query.  In an empty
        # projection, report fast-mlsirm as unavailable for this exact
        # visible/time window rather than claiming a persisted contract.
        return _unavailable_topic_context(tepp_ready)

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
