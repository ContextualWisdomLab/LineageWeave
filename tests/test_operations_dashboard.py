"""Focused tests for the operational dashboard evidence projection."""

import asyncio

from datetime import date, datetime, timezone
import json
from pathlib import Path
from uuid import UUID

import pytest

from backend.app.operations_dashboard import (
    _decode_case_cursor,
    _encode_case_cursor,
    _project_lifecycles,
    fetch_operations_dashboard,
)
from lineageweave.operations_case_analysis import REQUIRED_FACT_TYPES


def test_dashboard_read_projection_is_transactionally_maintained_and_replay_safe() -> None:
    """The narrow exact-count projection follows every authoritative mutation."""
    migration = Path("migrations/0264_dashboard_post_read_projection.sql").read_text()

    assert "create table if not exists dashboard_post_read_projection" in migration
    assert "on conflict (source_post_id) do update" in migration
    assert "dashboard_source_post_read_projection_trigger" in migration
    assert "dashboard_case_analysis_read_projection_trigger" in migration
    assert "dashboard_ingestion_job_read_projection_trigger" in migration
    assert "exists (select 1 from operations_case_analysis" in migration
    assert "exists (select 1 from post_content_ingestion_job" in migration
    assert "create table if not exists dashboard_case_rollup_read_projection" in migration
    assert "dashboard_case_rollup_classification_trigger" in migration
    assert "dashboard_case_rollup_milestone_trigger" in migration
    assert "dashboard_case_rollup_missing_milestone_trigger" in migration
    assert "create table if not exists dashboard_case_milestone_read_projection" in migration
    assert "create table if not exists dashboard_case_contributor_read_projection" in migration
    assert "dashboard_case_rollup_fact_trigger" in migration
    assert "dashboard_case_rollup_product_relation_trigger" in migration
    assert "create table if not exists dashboard_post_daily_summary" in migration
    assert "after insert or update or delete on dashboard_post_read_projection" in migration
    assert "if tg_op in ('UPDATE', 'DELETE') and old.active_source" in migration
    assert "if tg_op in ('INSERT', 'UPDATE') and new.active_source" in migration
    assert "group by occurred_date, visibility_code, corporate_entity_id, process_unit_id" in migration
    assert "dashboard_case_rollup_project_mention_trigger" in migration
    assert "dashboard_case_rollup_post_projection_trigger" in migration
    assert "dashboard_case_rollup_post_project_code_trigger" in migration
    assert "add column if not exists source_project_code text" in migration
    assert "projection.source_project_code is distinct from post.source_project_code" in migration
    assert (
        "coalesce(nullif(btrim(post.source_project_name), ''), project.primary_project_name,\n"
        "                    nullif(btrim(post.source_project_code), ''))"
        in migration
    )
    assert "after update of source_project_code on dashboard_post_read_projection" in migration


def test_dashboard_rejects_a_rollup_with_any_unauthorized_contributor() -> None:
    """Complete counts and pages share the normalized contributor ABAC guard."""
    conn = _Connection()
    asyncio.run(fetch_operations_dashboard(conn, []))
    statement = conn.queries[0][0]
    assert statement.count("dashboard_case_contributor_read_projection contributor") == 2
    assert "contributor_evidence.source_post_id is null" in statement
    assert "or not (" in statement


class _Connection:
    """Return deterministic rows while retaining the executed SQL."""

    tepp_ready = False
    fast_ready = False

    def __init__(self) -> None:
        self.queries: list[tuple[str, tuple[object, ...]]] = []

    async def fetchrow(self, query: str, *args: object) -> dict[str, int]:
        self.queries.append((query, args))
        if "dashboard_single_statement" in query:
            query_count = len(self.queries)
            result = {
                "metrics": ({
                    "total_post_count": 0,
                    "external_post_count": 0,
                    "pending_analysis_count": 0,
                    "failed_analysis_count": 0,
                } if getattr(self, "empty", False) else {
                    "total_post_count": 4,
                    "external_post_count": 1,
                    "pending_analysis_count": 1,
                    "failed_analysis_count": 2,
                }),
                "case_rollups": ([] if getattr(self, "empty", False) else await self.fetch("/* dashboard_case_rollup */")),
                "cases": ([] if getattr(self, "empty", False) or getattr(self, "hide_cases", False) else await self.fetch("limit $9")),
                "details": ([] if getattr(self, "empty", False) else await self.fetch("select row_kind, payload")),
                "topic_readiness": {
                    "topic_tepp_ready": self.tepp_ready,
                    "topic_fast_ready": self.fast_ready,
                },
                "topic_details": await self.fetch(
                    "from topic_post_context_influence influence", None, None, None, None
                ),
            }
            del self.queries[query_count:]
            return result
        if "tepp_posterior_persisted" in query:
            assert len(args) == 4
            return {
                "tepp_posterior_persisted": False,
                "fast_mlsirm_influence_persisted": False,
            }
        return {
            "total_post_count": 4,
            "total_event_count": 3,
            "external_post_count": 1,
            "pending_analysis_count": 1,
            "failed_analysis_count": 2,
        }

    async def fetch(self, query: str, *args: object) -> list[dict[str, object]]:
        self.queries.append((query, args))
        if "dashboard_case_rollup" in query:
            return [{
                "post_id": "00000000-0000-0000-0000-000000000001",
                "case_kind_code": "claim_investigation",
                "case_analysis_present": True,
                "ingestion_failed": False,
                "event_count": 2,
                "claim_started": True,
                "claim_ended": True,
                "rebid_started": False,
                "rebid_ended": False,
                "handover_started": False,
                "handover_ended": False,
                "claim_start_missing": False,
                "rebid_start_missing": False,
                "handover_start_missing": False,
            }]
        if "select row_kind, payload" in query:
            return [
                {
                    "row_kind": "fact",
                    "payload": {
                        "post_id": "00000000-0000-0000-0000-000000000001",
                        "case_kind_code": "claim_investigation",
                        "fact_type_code": "originating_order",
                        "value_text": "Synthetic order 7",
                        "evidence_text": "Synthetic cited sentence",
                        "evidence_post_id": "00000000-0000-0000-0000-000000000002",
                        "fact_ordinal": 0,
                        "relation_target_kind_code": None,
                    },
                },
                {
                    "row_kind": "missing_fact",
                    "payload": {
                        "post_id": "00000000-0000-0000-0000-000000000001",
                        "case_kind_code": "claim_investigation",
                        "fact_type_code": "sales_pool",
                    },
                },
                *[
                    {
                        "row_kind": "milestone",
                        "payload": {
                            "post_id": "00000000-0000-0000-0000-000000000001",
                            "case_kind_code": "claim_investigation",
                            "milestone_type_code": milestone_type,
                            "evidence_text": evidence_text,
                            "evidence_post_id": evidence_post_id,
                            "observed_at": observed_at.isoformat(),
                            "time_axis_code": time_axis,
                            "is_missing": False,
                        },
                    }
                    for milestone_type, evidence_text, evidence_post_id, observed_at, time_axis in (
                        ("claim_received", "The claim was received", "00000000-0000-0000-0000-000000000001", datetime(2026, 8, 1, 9, tzinfo=timezone.utc), "event_occurred_at"),
                        ("cause_confirmed", "The cause was confirmed", "00000000-0000-0000-0000-000000000002", datetime(2026, 8, 3, 12, 30, tzinfo=timezone.utc), "created_at"),
                    )
                ],
            ]
        if "product_operations_fact_relation relation" in query:
            return []
        if "operations_case_missing_fact missing" in query:
            return [{
                "post_id": "00000000-0000-0000-0000-000000000001",
                "case_kind_code": "claim_investigation",
                "fact_type_code": "sales_pool",
            }]
        if "operations_case_fact fact" in query:
            return [
                {
                    "post_id": "00000000-0000-0000-0000-000000000001",
                    "case_kind_code": "claim_investigation",
                    "fact_type_code": "originating_order",
                    "value_text": "Synthetic order 7",
                    "evidence_text": "Synthetic cited sentence",
                    "evidence_post_id": "00000000-0000-0000-0000-000000000002",
                    "fact_ordinal": 0,
                    "relation_target_kind_code": None,
                }
            ]
        if "operations_case_milestone milestone" in query:
            return [
                {
                    "post_id": "00000000-0000-0000-0000-000000000001",
                    "case_kind_code": "claim_investigation",
                    "milestone_type_code": "claim_received",
                    "evidence_text": "The claim was received",
                    "evidence_post_id": "00000000-0000-0000-0000-000000000001",
                    "observed_at": datetime(2026, 8, 1, 9, tzinfo=timezone.utc),
                    "time_axis_code": "event_occurred_at",
                    "is_missing": False,
                },
                {
                    "post_id": "00000000-0000-0000-0000-000000000001",
                    "case_kind_code": "claim_investigation",
                    "milestone_type_code": "cause_confirmed",
                    "evidence_text": "The cause was confirmed",
                    "evidence_post_id": "00000000-0000-0000-0000-000000000002",
                    "observed_at": datetime(2026, 8, 3, 12, 30, tzinfo=timezone.utc),
                    "time_axis_code": "created_at",
                    "is_missing": False,
                },
            ]
        if "from topic_post_context_influence influence" in query:
            assert len(args) == 4
            return []
        return [
            {
                "post_id": "00000000-0000-0000-0000-000000000001",
                "case_kind_code": "claim_investigation",
                "summary_text": "원인 수주가 연결됨",
                "evidence_text": "Synthetic cited sentence",
                "evidence_post_id": "00000000-0000-0000-0000-000000000002",
                "project_name": "Synthetic Project",
                "project_names": ["Synthetic Project", "Synthetic Secondary Project"],
                "project_keys": ["SYNTHETIC-PROJECT-100", "synthetic-secondary-project"],
                "project_key_labels": ["Synthetic Project", "Synthetic Secondary Project"],
                "project_key_provenances": [
                    "source_post.source_project_code",
                    "post_project_mention.project_key",
                ],
                "occurred_at": datetime(2026, 8, 12, tzinfo=timezone.utc),
            }
        ]


def test_projected_start_with_unavailable_end_remains_open() -> None:
    """A hidden end citation cannot make an observed start look absent."""
    start = {
        "milestone_type_code": "claim_received",
        "milestone_type_label": "클레임 접수",
        "evidence_text": "Synthetic claim received",
        "evidence_post_id": "synthetic-start",
        "observed_at": "2026-08-01T09:00:00+00:00",
        "time_axis_code": "event_occurred_at",
        "time_axis_label": "사건 발생일",
    }

    lifecycle = _project_lifecycles("claim_investigation", [start], set())[0]

    assert lifecycle["status_code"] == "open"
    assert lifecycle["start_milestone"] == start
    assert lifecycle["end_milestone"] is None
    assert lifecycle["next_action_text"] == "원인 확정 Event 근거를 연결하세요."


def test_dashboard_case_cursor_round_trips_a_stable_key() -> None:
    """Continuation retains the exact descending-time case key and rejects junk."""
    occurred_at = datetime(2026, 8, 31, 9, tzinfo=timezone.utc)
    cursor = _encode_case_cursor({
        "occurred_at": occurred_at,
        "post_id": "00000000-0000-0000-0000-000000000001",
        "case_kind_code": "claim_investigation",
    })

    assert _decode_case_cursor(cursor) == (
        occurred_at,
        "00000000-0000-0000-0000-000000000001",
        "claim_investigation",
    )
    with pytest.raises(ValueError, match="last Dashboard case"):
        _decode_case_cursor("not-a-dashboard-cursor")


@pytest.mark.anyio
async def test_dashboard_bounds_details_without_shrinking_exact_rollup() -> None:
    """A page limit constrains detail SQL while headline counts use every case."""

    class BoundedConnection(_Connection):
        async def fetch(self, query: str, *args: object) -> list[dict[str, object]]:
            if "dashboard_case_rollup" in query:
                first = (await super().fetch(query, *args))[0]
                return [first, {**first, "post_id": "00000000-0000-0000-0000-000000000003"}]
            if "limit $9" in query:
                self.queries.append((query, args))
                first = (await _Connection().fetch(query, *args))[0]
                return [
                    first,
                    {
                        **first,
                        "post_id": "00000000-0000-0000-0000-000000000003",
                        "occurred_at": datetime(2026, 8, 11, tzinfo=timezone.utc),
                    },
                ]
            return await super().fetch(query, *args)

    connection = BoundedConnection()
    result = await fetch_operations_dashboard(connection, [], case_limit=1)

    assert result["case_metrics"][0]["post_count"] == 2
    assert len(result["cases"]) == 1
    assert result["next_case_cursor"]
    assert len(connection.queries) == 1
    query, args = connection.queries[0]
    assert "selected_case as materialized" in query
    assert args[8] == 1


@pytest.mark.anyio
async def test_dashboard_reads_evidence_bound_product_relation() -> None:
    """A visible relation is attached to its exact persisted fact target."""

    class ProductRelationConnection(_Connection):
        async def fetch(self, query: str, *args: object) -> list[dict[str, object]]:
            rows = await super().fetch(query, *args)
            if "select row_kind, payload" in query:
                rows.append({"row_kind": "product", "payload": {
                    "post_id": "00000000-0000-0000-0000-000000000001",
                    "case_kind_code": "claim_investigation", "fact_ordinal": 0,
                    "relation_type_code": "concerns_product",
                    "extracted_product_name": "Synthetic Product",
                    "canonical_product_name": None, "evidence_text": "Synthetic cited sentence",
                    "evidence_post_id": "00000000-0000-0000-0000-000000000002",
                }})
                return rows
            return rows

    result = await fetch_operations_dashboard(ProductRelationConnection(), [])
    assert result["cases"][0]["facts"][0]["product_relations"] == [{
        "relation_type_code": "concerns_product",
        "product_name": "Synthetic Product",
        "evidence_text": "Synthetic cited sentence",
        "evidence_post_id": "00000000-0000-0000-0000-000000000002",
    }]


@pytest.mark.anyio
async def test_dashboard_rejects_malformed_product_relation_rows() -> None:
    """A broken query projection must fail instead of hiding relation evidence."""

    class MalformedProductRelationConnection(_Connection):
        async def fetch(self, query: str, *args: object) -> list[dict[str, object]]:
            rows = await super().fetch(query, *args)
            if "select row_kind, payload" in query:
                rows.append({"row_kind": "product", "payload": {
                    "post_id": "00000000-0000-0000-0000-000000000001"
                }})
            return rows

    with pytest.raises(KeyError, match="case_kind_code"):
        await fetch_operations_dashboard(MalformedProductRelationConnection(), [])


@pytest.mark.anyio
async def test_dashboard_uses_abac_event_clock_and_persisted_evidence() -> None:
    """Counts and cases share the exact authorized event-time population."""
    conn = _Connection()

    result = await fetch_operations_dashboard(
        conn,
        ["00000000-0000-0000-0000-000000000009"],
        ["00000000-0000-0000-0000-000000000008"],
        date(2026, 8, 1),
        date(2026, 8, 31),
    )

    assert result["period_label"] == "2026-08-01 ~ 2026-08-31 · 사건 발생일"
    assert result["project_history_knowledge_cutoff"] == (
        "2026-08-31T23:59:59.999999+09:00"
    )
    assert result["external_percent"] == 25.0
    assert result["failed_analysis_count"] == 2
    assert result["case_metrics"] == [
        {
            "case_kind_code": "claim_investigation",
            "case_kind_label": "클레임 원인 규명",
            "event_count": 2,
            "post_count": 1,
        },
        {
            "case_kind_code": "rebid_handover",
            "case_kind_label": "재입찰 · 인수인계",
            "event_count": 0,
            "post_count": 0,
        },
        {
            "case_kind_code": "external_information",
            "case_kind_label": "발주 공고 · 시장 동향",
            "event_count": 0,
            "post_count": 0,
        },
        {
            "case_kind_code": "repeat_issue",
            "case_kind_label": "반복 이슈",
            "event_count": 0,
            "post_count": 0,
        },
    ]
    semantic_projection = result["cases"][0].pop("semantic_projection")
    assert semantic_projection["@type"][0].endswith("#ClaimInvestigation")
    assert semantic_projection["prov:wasDerivedFrom"]["@id"].endswith(
        "00000000-0000-0000-0000-000000000002"
    )
    assert result["cases"] == [
        {
            "post_id": "00000000-0000-0000-0000-000000000001",
            "case_kind_code": "claim_investigation",
            "case_kind_label": "클레임 원인 규명",
            "project_name": "Synthetic Project",
            "project_names": ["Synthetic Project", "Synthetic Secondary Project"],
            "projects": [
                {
                    "project_key": "SYNTHETIC-PROJECT-100",
                    "project_name": "Synthetic Project",
                    "key_provenance": "source_post.source_project_code",
                    "evidence_post_id": "00000000-0000-0000-0000-000000000001",
                },
                {
                    "project_key": "synthetic-secondary-project",
                    "project_name": "Synthetic Secondary Project",
                    "key_provenance": "post_project_mention.project_key",
                    "evidence_post_id": "00000000-0000-0000-0000-000000000001",
                },
            ],
            "summary_text": "원인 수주가 연결됨",
            "evidence_text": "Synthetic cited sentence",
            "evidence_post_id": "00000000-0000-0000-0000-000000000002",
            "ontology_class_iri": "https://contextualwisdomlab.github.io/LineageWeave/ontology#ClaimInvestigation",
            "provenance_relation_iri": "http://www.w3.org/ns/prov#wasDerivedFrom",
            "occurred_at": "2026-08-12T00:00:00+00:00",
            "facts": [
                {
                    "fact_type_code": "originating_order",
                    "fact_type_label": "원인 수주",
                    "value_text": "Synthetic order 7",
                    "evidence_text": "Synthetic cited sentence",
                    "evidence_post_id": "00000000-0000-0000-0000-000000000002",
                    "ontology_class_iri": "https://contextualwisdomlab.github.io/LineageWeave/ontology#OperationsCaseFact",
                    "provenance_relation_iri": "http://www.w3.org/ns/prov#wasDerivedFrom",
                }
            ],
            "missing_facts": [
                {"fact_type_code": "sales_pool", "fact_type_label": "수주 Pool"}
            ],
            "milestones": [
                {
                    "milestone_type_code": "claim_received",
                    "milestone_type_label": "클레임 접수",
                    "evidence_text": "The claim was received",
                    "evidence_post_id": "00000000-0000-0000-0000-000000000001",
                    "observed_at": "2026-08-01T09:00:00+00:00",
                    "time_axis_code": "event_occurred_at",
                    "time_axis_label": "사건 발생일",
                },
                {
                    "milestone_type_code": "cause_confirmed",
                    "milestone_type_label": "원인 확정",
                    "evidence_text": "The cause was confirmed",
                    "evidence_post_id": "00000000-0000-0000-0000-000000000002",
                    "observed_at": "2026-08-03T12:30:00+00:00",
                    "time_axis_code": "created_at",
                    "time_axis_label": "기록 생성일",
                },
            ],
            "lifecycles": [
                {
                    "lifecycle_kind_code": "claim_investigation",
                    "lifecycle_kind_label": "클레임 원인 규명",
                    "status_code": "resolved",
                    "status_label": "종료 확인",
                    "started_at": "2026-08-01T09:00:00+00:00",
                    "resolved_at": "2026-08-03T12:30:00+00:00",
                    "elapsed_seconds": 185400,
                    "start_milestone": {
                        "milestone_type_code": "claim_received",
                        "milestone_type_label": "클레임 접수",
                        "evidence_text": "The claim was received",
                        "evidence_post_id": "00000000-0000-0000-0000-000000000001",
                        "observed_at": "2026-08-01T09:00:00+00:00",
                        "time_axis_code": "event_occurred_at",
                        "time_axis_label": "사건 발생일",
                    },
                    "end_milestone": {
                        "milestone_type_code": "cause_confirmed",
                        "milestone_type_label": "원인 확정",
                        "evidence_text": "The cause was confirmed",
                        "evidence_post_id": "00000000-0000-0000-0000-000000000002",
                        "observed_at": "2026-08-03T12:30:00+00:00",
                        "time_axis_code": "created_at",
                        "time_axis_label": "기록 생성일",
                    },
                    "next_action_text": "시작·종료 사건 근거를 열어 경과 시간을 검토하세요.",
                }
            ],
        }
    ]
    case_statement = next(
        query for query, _ in conn.queries if "from operations_case_classification" in query
    )
    assert "post.source_project_code), '')\n                                   as project_key" in case_statement
    assert "key_mention.project_key), '')" in case_statement
    assert "select nullif(btrim(post.source_project_name), '')" not in case_statement
    assert result["topic_context"]["status_code"] == "unavailable"
    assert result["topic_context"]["reason_code"] == "tepp_topic_posterior_not_persisted"
    assert len(conn.queries) == 1
    query, args = conn.queries[0]
    assert "dashboard_single_statement" in query
    assert "visibility_code = 'public'" in query
    assert "corporate_entity_id = any($1::uuid[])" in query
    assert "process_unit_id = any($2::uuid[])" in query
    assert args[:2] == (
        [UUID("00000000-0000-0000-0000-000000000009")],
        [UUID("00000000-0000-0000-0000-000000000008")],
    )
    assert args[2:9] == (
        date(2026, 8, 1), date(2026, 8, 31), False,
        None, None, None, 20,
    )
    assert json.loads(args[9]) == {
        case_kind: sorted(fact_types)
        for case_kind, fact_types in REQUIRED_FACT_TYPES.items()
    }
    assert "dashboard_case_rollup_read_projection rollup" in query
    assert "order by rollup.occurred_at desc" in query
    assert "operations_case_missing_fact missing" in query
    assert "($10::jsonb -> fact.case_kind_code) ? fact.fact_type_code" in query
    assert "post_summary_event" not in query


@pytest.mark.anyio
async def test_dashboard_counts_each_case_milestone_set_once() -> None:
    """Multiple classification evidence rows cannot duplicate one case's events."""

    class DuplicateClassificationConnection(_Connection):
        async def fetch(self, query: str, *args: object) -> list[dict[str, object]]:
            rows = await super().fetch(query, *args)
            if (
                "operations_case_classification classification" in query
                and "dashboard_case_rollup" not in query
            ):
                return [rows[0], {**rows[0], "evidence_post_id": "00000000-0000-0000-0000-000000000003"}]
            return rows

    result = await fetch_operations_dashboard(DuplicateClassificationConnection(), [])

    assert result["total_event_count"] == 2
    assert result["case_metrics"][0]["event_count"] == 2


@pytest.mark.anyio
async def test_dashboard_headline_excludes_hidden_milestone_evidence() -> None:
    """Headline and per-type counts share the evidence-visible milestone rows."""

    class HiddenMilestoneConnection(_Connection):
        async def fetch(self, query: str, *args: object) -> list[dict[str, object]]:
            if "/* dashboard_case_rollup */" in query:
                self.queries.append((query, args))
                return []
            return await super().fetch(query, *args)

    result = await fetch_operations_dashboard(HiddenMilestoneConnection(), [])

    assert result["total_event_count"] == 0
    assert sum(metric["event_count"] for metric in result["case_metrics"]) == 0


@pytest.mark.anyio
async def test_dashboard_event_counts_exclude_hidden_classification_evidence() -> None:
    """A milestone cannot outlive the visible classification that owns it."""

    class HiddenClassificationConnection(_Connection):
        hide_cases = True
        async def fetch(self, query: str, *args: object) -> list[dict[str, object]]:
            if (
                "/* dashboard_case_rollup */" in query
                or (
                    "from operations_case_classification classification" in query
                    and "operations_case_fact" not in query
                )
            ):
                self.queries.append((query, args))
                return []
            return await super().fetch(query, *args)

    result = await fetch_operations_dashboard(HiddenClassificationConnection(), [])

    assert result["cases"] == []
    assert result["total_event_count"] == 0
    assert sum(metric["event_count"] for metric in result["case_metrics"]) == 0


@pytest.mark.anyio
async def test_dashboard_projects_exact_topic_influence_without_local_scoring() -> None:
    """Accepted rows retain ties, membership evidence, and producer identity."""

    class TopicConnection(_Connection):
        provenance_complete = True
        tepp_ready = True
        fast_ready = True

        async def fetchrow(self, query: str, *args: object) -> dict[str, object]:
            if "tepp_posterior_persisted" in query:
                self.queries.append((query, args))
                return {
                    "tepp_posterior_persisted": True,
                    "fast_mlsirm_influence_persisted": True,
                }
            return await super().fetchrow(query, *args)

        async def fetch(self, query: str, *args: object) -> list[dict[str, object]]:
            if "from topic_post_context_influence influence" not in query:
                return await super().fetch(query, *args)
            self.queries.append((query, args))
            common = {
                "topic_model_run_id": "model-1",
                "tepp_run_id": "tepp-1",
                "tepp_snapshot_id": "tepp-snapshot-1",
                "tepp_schema_version": "tepp.topic_context_posterior.v1",
                "tepp_model_contract_version": "trsl-tm-1",
                "tepp_artifact_sha256": "a" * 64,
                "posterior_draw_set_id": "draws-1",
                "posterior_draw_count": 32,
                "topic_count": 2,
                "source_snapshot_sha256": "b" * 64,
                "knowledge_cutoff": datetime(2026, 8, 20, tzinfo=timezone.utc),
                "topic_influence_run_id": "influence-1",
                "fast_mlsirm_schema_version": "fast_mlsirm.topic_context_influence.v1",
                "fast_mlsirm_version": "0.1.0",
                "fast_mlsirm_code_revision": "c" * 40,
                "fast_mlsirm_artifact_sha256": "d" * 64,
                "compute_backend_code": "rust_gpu",
                "precision_code": "f64",
                "membership_fingerprint_sha256": "e" * 64,
                "topic_index": 0,
                "state_code": "reactivated",
                "activity_valid_from": datetime(2026, 8, 1, tzinfo=timezone.utc),
                "activity_valid_to": datetime(2026, 9, 1, tzinfo=timezone.utc),
                "dimension_code": "team",
                "context_id": "team-synthetic",
                "context_label": "Synthetic Service Team",
                "membership_weight": 0.5,
                "membership_evidence_post_id": "00000000-0000-0000-0000-000000000099",
                "occurred_at": datetime(2026, 8, 12, tzinfo=timezone.utc),
                "influence_value": 4.25,
                "uncertainty_method_code": "posterior_interval",
                "uncertainty_lower_value": 3.5,
                "uncertainty_upper_value": 5.0,
                "diagnostic_status_code": "accepted",
                "provenance_complete": self.provenance_complete,
                "lineage_events": '[{"event_code":"birth","source_topic_index":0,"target_topic_index":null,"event_time":"2026-08-01T00:00:00+00:00","evidence_post_id":"00000000-0000-0000-0000-000000000098"}]',
            }
            return [
                {**common, "source_post_id": "00000000-0000-0000-0000-000000000001"},
                {
                    **common,
                    "source_post_id": "00000000-0000-0000-0000-000000000002",
                    "lineage_events": [{"event_code": "birth"}],
                },
            ]

    result = await fetch_operations_dashboard(TopicConnection(), [])
    topic_context = result["topic_context"]
    assert topic_context["status_code"] == "accepted"
    assert topic_context["model_run"]["compute_backend_code"] == "rust_gpu"
    influences = topic_context["topics"][0]["contexts"][0]["influences"]
    assert [item["model_influence"] for item in influences] == [4.25, 4.25]
    assert influences[0]["membership_weight"] == 0.5
    assert topic_context["topics"][0]["lineage_events"][0]["event_code"] == "birth"
    assert topic_context["topics"][0]["lineage_events"][0]["evidence_post_id"].endswith("98")
    assert influences[0]["membership_evidence_post_id"].endswith("99")

    incomplete = TopicConnection()
    incomplete.provenance_complete = False
    unavailable = (await fetch_operations_dashboard(incomplete, []))["topic_context"]
    assert unavailable["status_code"] == "unavailable"
    assert unavailable["reason_code"] == "topic_context_provenance_not_navigable"
    assert unavailable["topics"] == []
    projection_sql = incomplete.queries[0][0]
    assert "topic_candidate as materialized" in projection_sql
    assert "left join visible_post checked_visible" in projection_sql
    assert "join visible_post post on post.source_post_id = membership.source_post_id" in projection_sql


@pytest.mark.anyio
async def test_dashboard_names_missing_fast_result_after_tepp_persistence() -> None:
    """A persisted TEPP membership never becomes a fabricated influence value."""

    class TeppOnlyConnection(_Connection):
        tepp_ready = True
        async def fetchrow(self, query: str, *args: object) -> dict[str, object]:
            if "tepp_posterior_persisted" in query:
                self.queries.append((query, args))
                return {
                    "tepp_posterior_persisted": True,
                    "fast_mlsirm_influence_persisted": False,
                }
            return await super().fetchrow(query, *args)

    connection = TeppOnlyConnection()
    result = await fetch_operations_dashboard(connection, [])
    assert result["topic_context"]["reason_code"] == "fast_mlsirm_influence_not_persisted"
    assert result["topic_context"]["topics"] == []
    assert not any("candidate_runs as" in query for query, _args in connection.queries)


@pytest.mark.anyio
async def test_empty_projection_does_not_claim_fast_result_persisted() -> None:
    """An empty visible projection must not contradict its contract state."""

    class ReadyButEmptyConnection(_Connection):
        tepp_ready = True
        fast_ready = True
        async def fetchrow(self, query: str, *args: object) -> dict[str, object]:
            if "tepp_posterior_persisted" in query:
                self.queries.append((query, args))
                return {
                    "tepp_posterior_persisted": True,
                    "fast_mlsirm_influence_persisted": True,
                }
            return await super().fetchrow(query, *args)

    result = await fetch_operations_dashboard(ReadyButEmptyConnection(), [])
    contracts = result["topic_context"]["required_contracts"]
    assert contracts[0]["state_code"] == "persisted"
    assert contracts[1]["state_code"] == "not_persisted"


@pytest.mark.anyio
async def test_topic_readiness_uses_projection_temporal_windows() -> None:
    """Readiness cannot count influence rows the projection must reject by time."""
    conn = _Connection()
    await fetch_operations_dashboard(conn, [])
    readiness_query = conn.queries[0][0]
    assert "topic_tepp_ready" in readiness_query
    assert "visible_post.occurred_at >= membership.valid_from" in readiness_query
    assert "visible_post.occurred_at < membership.valid_to" in readiness_query
    assert "join topic_activity_interval activity" in readiness_query
    assert "post.occurred_at >= activity.valid_from" in readiness_query
    assert "post.occurred_at < activity.valid_to" in readiness_query

@pytest.mark.anyio
async def test_external_scope_filters_cases_without_shrinking_coverage_denominator() -> None:
    """External-only cases retain all visible posts as the percentage denominator."""
    conn = _Connection()
    await fetch_operations_dashboard(
        conn,
        ["00000000-0000-0000-0000-000000000009"],
        ["00000000-0000-0000-0000-000000000008"],
        date(2026, 8, 1),
        date(2026, 8, 31),
        external_only=True,
    )
    assert conn.queries
    metrics_query, metrics_args = conn.queries[0]
    assert "sum(summary.total_post_count)" in metrics_query
    assert "group by classification.post_id" in metrics_query
    assert "select count(*) from external_post" in metrics_query
    assert "$5::boolean" in metrics_query
    assert metrics_args[4] is True


@pytest.mark.anyio
async def test_dashboard_zero_denominator_and_invalid_period() -> None:
    """An empty corpus has 0%, while an inverted interval fails closed."""

    class EmptyConnection(_Connection):
        empty = True

    empty = await fetch_operations_dashboard(EmptyConnection(), [])
    assert empty["external_percent"] == 0.0
    assert all(metric["event_count"] == metric["post_count"] == 0 for metric in empty["case_metrics"])
    assert (await fetch_operations_dashboard(EmptyConnection(), [], [], date(2026, 8, 1)))["period_label"] == "2026-08-01 이후 · 사건 발생일"
    assert (await fetch_operations_dashboard(EmptyConnection(), [], [], None, date(2026, 8, 31)))["period_label"] == "2026-08-31 이전 · 사건 발생일"
    with pytest.raises(ValueError, match="period_start"):
        await fetch_operations_dashboard(
            EmptyConnection(), [], [], date(2026, 9, 1), date(2026, 8, 31)
        )


@pytest.mark.anyio
async def test_external_information_projects_a_typed_prov_o_relation() -> None:
    """A cited semantic target becomes RDF reification, never a KG alias."""

    class ExternalConnection(_Connection):
        async def fetchrow(self, query: str, *args: object) -> dict[str, object]:
            if "tepp_posterior_persisted" in query:
                self.queries.append((query, args))
                return {
                    "tepp_posterior_persisted": False,
                    "fast_mlsirm_influence_persisted": False,
                }
            return await super().fetchrow(query, *args)

        async def fetch(self, query: str, *args: object) -> list[dict[str, object]]:
            self.queries.append((query, args))
            if "/* dashboard_case_rollup */" in query:
                return []
            if "from topic_post_context_influence influence" in query:
                return []
            if "select row_kind, payload" in query:
                return [{"row_kind": "fact", "payload": {
                    "post_id": "00000000-0000-0000-0000-000000000001",
                    "case_kind_code": "external_information",
                    "fact_type_code": "external_relation", "value_text": "Synthetic Project",
                    "evidence_text": "Synthetic tender evidence",
                    "evidence_post_id": "00000000-0000-0000-0000-000000000002",
                    "fact_ordinal": 0, "relation_target_kind_code": "project",
                }}]
            return [{
                "post_id": "00000000-0000-0000-0000-000000000001",
                "case_kind_code": "external_information",
                "summary_text": "External tender",
                "evidence_text": "Synthetic tender evidence",
                "evidence_post_id": "00000000-0000-0000-0000-000000000002",
                "project_name": "Synthetic Project",
                "project_names": ["Synthetic Project"],
                "project_keys": ["synthetic-project"],
                "project_key_labels": ["Synthetic Project"],
                "project_key_provenances": ["post_project_mention.project_key"],
                "occurred_at": datetime(2026, 8, 12, tzinfo=timezone.utc),
            }]

    result = await fetch_operations_dashboard(ExternalConnection(), [])

    fact = result["cases"][0]["facts"][0]
    assert fact["relation_target_kind_code"] == "project"
    assert fact["relation_predicate_iri"].endswith("#relatesToProject")
    statement = result["cases"][0]["semantic_projection"][
        "https://contextualwisdomlab.github.io/LineageWeave/ontology#hasOperationsFact"
    ][0]
    assert statement["http://www.w3.org/1999/02/22-rdf-syntax-ns#predicate"] == {
        "@id": fact["relation_predicate_iri"]
    }
    assert statement["http://www.w3.org/ns/prov#wasDerivedFrom"]["@id"].endswith(
        "00000000-0000-0000-0000-000000000002"
    )
    target = statement["http://www.w3.org/1999/02/22-rdf-syntax-ns#object"]
    assert target["@id"].endswith(":fact:0:target")
    assert target["@type"].endswith("#Project")


@pytest.fixture
def anyio_backend() -> str:
    """Use the installed asyncio backend for async projection tests."""
    return "asyncio"
