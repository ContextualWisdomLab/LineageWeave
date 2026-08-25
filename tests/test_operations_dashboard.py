"""Focused tests for the operational dashboard evidence projection."""

from datetime import date, datetime, timezone

import pytest

from backend.app.operations_dashboard import fetch_operations_dashboard


class _Connection:
    """Return deterministic rows while retaining the executed SQL."""

    def __init__(self) -> None:
        self.queries: list[tuple[str, tuple[object, ...]]] = []

    async def fetchrow(self, query: str, *args: object) -> dict[str, int]:
        self.queries.append((query, args))
        if "tepp_posterior_persisted" in query:
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
                }
            ]
        if "operations_case_missing_fact missing" in query:
            return [{
                "post_id": "00000000-0000-0000-0000-000000000001",
                "case_kind_code": "claim_investigation",
                "fact_type_code": "sales_pool",
            }]
        if "from topic_post_context_influence influence" in query:
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
            "occurred_at": "2026-08-12T00:00:00+00:00",
            "facts": [
                {
                    "fact_type_code": "originating_order",
                    "fact_type_label": "원인 수주",
                    "value_text": "Synthetic order 7",
                    "evidence_text": "Synthetic cited sentence",
                    "evidence_post_id": "00000000-0000-0000-0000-000000000002",
                }
            ],
            "missing_facts": [
                {"fact_type_code": "sales_pool", "fact_type_label": "수주 Pool"}
            ],
        }
    ]
    assert result["topic_context"]["status_code"] == "unavailable"
    assert result["topic_context"]["reason_code"] == "tepp_topic_posterior_not_persisted"
    assert len(conn.queries) == 6
    for query, args in conn.queries:
        assert "visibility_code = 'public'" in query
        assert "corporate_entity_id::text = any($1::text[])" in query
        assert "process_unit_id::text = any($2::text[])" in query
        assert "coalesce(post.event_occurred_at, post.created_at)" in query
        assert args[1:] == (
            ["00000000-0000-0000-0000-000000000008"],
            date(2026, 8, 1),
            date(2026, 8, 31),
            False,
        )
    case_query = conn.queries[1][0]
    assert "order by primary_mention.confidence desc" in case_query
    assert "coalesce(nullif(btrim(post.source_project_name), ''), project.primary_project_name)" in case_query


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
async def test_external_scope_is_bound_in_every_dashboard_query() -> None:
    """The external destination restricts data at the API query boundary."""
    conn = _Connection()
    await fetch_operations_dashboard(
        conn, ["corp"], ["pu"], date(2026, 8, 1), date(2026, 8, 31), external_only=True
    )
    assert conn.queries
    assert all("$5::boolean" in query for query, _ in conn.queries)
    assert all(args[-1] is True for _, args in conn.queries)


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
                ("total_post_count", "total_event_count", "external_post_count", "pending_analysis_count", "failed_analysis_count"),
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


@pytest.fixture
def anyio_backend() -> str:
    """Use the installed asyncio backend for async projection tests."""
    return "asyncio"
