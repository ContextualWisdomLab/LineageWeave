"""Focused tests for the operational dashboard evidence projection."""

from datetime import date, datetime, timezone

import pytest

from backend.app.operations_dashboard import _project_lifecycles, fetch_operations_dashboard


class _Connection:
    """Return deterministic rows while retaining the executed SQL."""

    def __init__(self) -> None:
        self.queries: list[tuple[str, tuple[object, ...]]] = []

    async def fetchrow(self, query: str, *args: object) -> dict[str, int]:
        self.queries.append((query, args))
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
        if "operations_case_missing_fact missing" in query:
            return [{
                "post_id": "00000000-0000-0000-0000-000000000001",
                "case_kind_code": "claim_investigation",
                "fact_type_code": "sales_pool",
            }]
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
                    "occurred_at": datetime(2026, 8, 12, tzinfo=timezone.utc),
                    "event_count": 2,
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
        "time_axis_label": "Event 발생일",
    }

    lifecycle = _project_lifecycles("claim_investigation", [start], set())[0]

    assert lifecycle["status_code"] == "open"
    assert lifecycle["start_milestone"] == start
    assert lifecycle["end_milestone"] is None
    assert lifecycle["next_action_text"] == "원인 확정 Event 근거를 연결하세요."


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

    assert result["period_label"] == "2026-08-01 ~ 2026-08-31 · Event 발생일"
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
                    "time_axis_label": "Event 발생일",
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
                        "time_axis_label": "Event 발생일",
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
                    "next_action_text": "시작·종료 Event 근거를 열어 경과 시간을 검토하세요.",
                }
            ],
        }
    ]
    assert result["topic_context"]["status_code"] == "unavailable"
    assert result["topic_context"]["reason_code"] == "tepp_topic_posterior_not_persisted"
    assert len(conn.queries) == 7
    for query, args in conn.queries:
        assert "visibility_code = 'public'" in query
        assert "corporate_entity_id::text = any($1::text[])" in query
        assert "process_unit_id::text = any($2::text[])" in query
        assert "coalesce(post.event_occurred_at, post.created_at)" in query
        assert args[:4] == (
            ["00000000-0000-0000-0000-000000000009"],
            ["00000000-0000-0000-0000-000000000008"],
            date(2026, 8, 1),
            date(2026, 8, 31),
        )
        assert args[4:] == ((False,) if "$5" in query else ())
    case_query = conn.queries[1][0]
    assert "order by primary_mention.confidence desc" in case_query
    assert (
        "coalesce(nullif(btrim(post.source_project_name), ''), project.primary_project_name)"
        in case_query
    )
    assert "observed_at nulls last" in conn.queries[4][0]
    for evidence_query in (
        conn.queries[0][0],
        conn.queries[1][0],
        conn.queries[2][0],
    ):
        assert "join source_post evidence_post" in evidence_query
        assert "evidence_post.corporate_entity_id::text = any($1::text[])" in evidence_query


@pytest.mark.anyio
async def test_dashboard_projects_exact_topic_influence_without_local_scoring() -> None:
    """Accepted rows retain ties, membership evidence, and producer identity."""

    class TopicConnection(_Connection):
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
                "membership_evidence_sha256": "f" * 64,
                "occurred_at": datetime(2026, 8, 12, tzinfo=timezone.utc),
                "influence_value": 4.25,
                "uncertainty_method_code": "posterior_interval",
                "uncertainty_lower_value": 3.5,
                "uncertainty_upper_value": 5.0,
                "diagnostic_status_code": "accepted",
                "lineage_events": '[{"event_code":"birth","source_topic_index":0,"target_topic_index":null,"event_time":"2026-08-01T00:00:00+00:00","evidence_sha256":"' + "1" * 64 + '"}]',
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


@pytest.mark.anyio
async def test_dashboard_names_missing_fast_result_after_tepp_persistence() -> None:
    """A persisted TEPP membership never becomes a fabricated influence value."""

    class TeppOnlyConnection(_Connection):
        async def fetchrow(self, query: str, *args: object) -> dict[str, object]:
            if "tepp_posterior_persisted" in query:
                self.queries.append((query, args))
                return {
                    "tepp_posterior_persisted": True,
                    "fast_mlsirm_influence_persisted": False,
                }
            return await super().fetchrow(query, *args)

    result = await fetch_operations_dashboard(TeppOnlyConnection(), [])
    assert result["topic_context"]["reason_code"] == "fast_mlsirm_influence_not_persisted"
    assert result["topic_context"]["topics"] == []


@pytest.mark.anyio
async def test_empty_projection_does_not_claim_fast_result_persisted() -> None:
    """An empty visible projection must not contradict its contract state."""

    class ReadyButEmptyConnection(_Connection):
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
    readiness_query = next(
        query for query, _args in conn.queries if "tepp_posterior_persisted" in query
    )
    assert "coalesce(post.event_occurred_at, post.created_at) as occurred_at" in readiness_query
    assert "visible_post.occurred_at >= membership.valid_from" in readiness_query
    assert "visible_post.occurred_at < membership.valid_to" in readiness_query
    assert "join topic_activity_interval activity" in readiness_query
    assert "visible_post.occurred_at >= activity.valid_from" in readiness_query
    assert "visible_post.occurred_at < activity.valid_to" in readiness_query

@pytest.mark.anyio
async def test_external_scope_filters_cases_without_shrinking_coverage_denominator() -> None:
    """External-only cases retain all visible posts as the percentage denominator."""
    conn = _Connection()
    await fetch_operations_dashboard(
        conn, ["corp"], ["pu"], date(2026, 8, 1), date(2026, 8, 31), external_only=True
    )
    assert conn.queries
    metrics_query, metrics_args = conn.queries[0]
    assert "scoped_post" in metrics_query
    assert "count(*) from visible_post) as total_post_count" in metrics_query
    assert "count(*) from scoped_post) as total_post_count" not in metrics_query
    assert "$5::boolean" in metrics_query
    assert metrics_args[-1] is True
    for query, args in conn.queries[1:]:
        assert "$5::boolean" in query
        assert args[-1] is True


@pytest.mark.anyio
async def test_dashboard_zero_denominator_and_invalid_period() -> None:
    """An empty corpus has 0%, while an inverted interval fails closed."""

    class EmptyConnection(_Connection):
        async def fetchrow(self, query: str, *args: object) -> dict[str, int]:
            self.queries.append((query, args))
            if "tepp_posterior_persisted" in query:
                return {
                    "tepp_posterior_persisted": False,
                    "fast_mlsirm_influence_persisted": False,
                }
            return dict.fromkeys(
                (
                    "total_post_count",
                    "total_event_count",
                    "external_post_count",
                    "pending_analysis_count",
                    "failed_analysis_count",
                ),
                0,
            )

        async def fetch(self, query: str, *args: object) -> list[dict[str, object]]:
            self.queries.append((query, args))
            return []

    empty = await fetch_operations_dashboard(EmptyConnection(), [])
    assert empty["external_percent"] == 0.0
    assert all(metric["event_count"] == metric["post_count"] == 0 for metric in empty["case_metrics"])
    assert (await fetch_operations_dashboard(EmptyConnection(), [], [], date(2026, 8, 1)))["period_label"] == "2026-08-01 이후 · Event 발생일"
    assert (await fetch_operations_dashboard(EmptyConnection(), [], [], None, date(2026, 8, 31)))["period_label"] == "2026-08-31 이전 · Event 발생일"
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
            if "operations_case_milestone milestone" in query:
                return []
            if "from topic_post_context_influence influence" in query:
                return []
            if "operations_case_fact fact" in query:
                return [{
                    "post_id": "00000000-0000-0000-0000-000000000001",
                    "case_kind_code": "external_information",
                    "fact_type_code": "external_relation",
                    "value_text": "Synthetic Project",
                    "evidence_text": "Synthetic tender evidence",
                    "evidence_post_id": "00000000-0000-0000-0000-000000000002",
                    "fact_ordinal": 0,
                    "relation_target_kind_code": "project",
                }]
            if "operations_case_missing_fact missing" in query:
                return []
            return [{
                "post_id": "00000000-0000-0000-0000-000000000001",
                "case_kind_code": "external_information",
                "summary_text": "External tender",
                "evidence_text": "Synthetic tender evidence",
                "evidence_post_id": "00000000-0000-0000-0000-000000000002",
                "project_name": "Synthetic Project",
                "project_names": ["Synthetic Project"],
                "occurred_at": datetime(2026, 8, 12, tzinfo=timezone.utc),
                "event_count": 1,
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
