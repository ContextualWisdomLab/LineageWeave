"""Focused tests for the operational dashboard evidence projection."""

from datetime import UTC, date, datetime

import pytest

from backend.app.operations_dashboard import fetch_operations_dashboard


class _Connection:
    """Return deterministic rows while retaining the executed SQL."""

    def __init__(self) -> None:
        self.queries: list[tuple[str, tuple[object, ...]]] = []

    async def fetchrow(self, query: str, *args: object) -> dict[str, int]:
        self.queries.append((query, args))
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
            return [
                {
                    "post_id": "00000000-0000-0000-0000-000000000001",
                    "case_kind_code": "claim_investigation",
                    "fact_type_code": "sales_pool",
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
                    "observed_at": datetime(2026, 8, 1, 9, tzinfo=UTC),
                    "time_axis_code": "event_occurred_at",
                    "is_missing": False,
                },
                {
                    "post_id": "00000000-0000-0000-0000-000000000001",
                    "case_kind_code": "claim_investigation",
                    "milestone_type_code": "cause_confirmed",
                    "evidence_text": "The cause was confirmed",
                    "evidence_post_id": "00000000-0000-0000-0000-000000000002",
                    "observed_at": datetime(2026, 8, 3, 12, 30, tzinfo=UTC),
                    "time_axis_code": "created_at",
                    "is_missing": False,
                },
            ]
        return [
            {
                "post_id": "00000000-0000-0000-0000-000000000001",
                "case_kind_code": "claim_investigation",
                "summary_text": "원인 수주가 연결됨",
                "evidence_text": "Synthetic cited sentence",
                "evidence_post_id": "00000000-0000-0000-0000-000000000002",
                "project_name": "Synthetic Project",
                "project_names": ["Synthetic Project", "Synthetic Secondary Project"],
                "occurred_at": datetime(2026, 8, 12, tzinfo=UTC),
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
            "event_count": 1,
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
    assert result["lifecycle_metrics"] == [
        {
            "lifecycle_kind_code": "claim_investigation",
            "lifecycle_kind_label": "클레임 원인 규명",
            "open_case_count": 0,
            "resolved_case_count": 1,
            "evidence_missing_case_count": 0,
        },
        {
            "lifecycle_kind_code": "rebid_response",
            "lifecycle_kind_label": "재입찰 대응",
            "open_case_count": 0,
            "resolved_case_count": 0,
            "evidence_missing_case_count": 0,
        },
        {
            "lifecycle_kind_code": "handover_gap",
            "lifecycle_kind_label": "인수인계 공백",
            "open_case_count": 0,
            "resolved_case_count": 0,
            "evidence_missing_case_count": 0,
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
    assert len(conn.queries) == 5
    for query, args in conn.queries:
        assert "visibility_code = 'public'" in query
        assert "corporate_entity_id::text = any($1::text[])" in query
        assert "process_unit_id::text = any($2::text[])" in query
        assert "coalesce(post.event_occurred_at, post.created_at)" in query
        assert args[1:] == (
            ["00000000-0000-0000-0000-000000000008"],
            date(2026, 8, 1),
            date(2026, 8, 31),
        )
    case_query = conn.queries[1][0]
    assert "order by primary_mention.confidence desc" in case_query
    assert (
        "coalesce(nullif(btrim(post.source_project_name), ''), project.primary_project_name)"
        in case_query
    )
    for evidence_query in (
        conn.queries[0][0],
        conn.queries[1][0],
        conn.queries[2][0],
        conn.queries[4][0],
    ):
        assert "join source_post evidence_post" in evidence_query
        assert "evidence_post.corporate_entity_id::text = any($1::text[])" in evidence_query


@pytest.mark.anyio
async def test_dashboard_zero_denominator_and_invalid_period() -> None:
    """An empty corpus has 0%, while an inverted interval fails closed."""

    class EmptyConnection(_Connection):
        async def fetchrow(self, query: str, *args: object) -> dict[str, int]:
            self.queries.append((query, args))
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
    assert all(
        metric["event_count"] == metric["post_count"] == 0
        for metric in empty["case_metrics"]
    )
    with pytest.raises(ValueError, match="period_start"):
        await fetch_operations_dashboard(
            EmptyConnection(), [], [], date(2026, 9, 1), date(2026, 8, 31)
        )


@pytest.mark.anyio
async def test_open_lifecycle_has_no_fabricated_elapsed_endpoint() -> None:
    """A known start plus a missing finish is open with nullable elapsed time."""

    class OpenConnection(_Connection):
        async def fetch(self, query: str, *args: object) -> list[dict[str, object]]:
            if "operations_case_milestone milestone" in query:
                return [
                    {
                        "post_id": "00000000-0000-0000-0000-000000000001",
                        "case_kind_code": "claim_investigation",
                        "milestone_type_code": "claim_received",
                        "evidence_text": "The claim was received",
                        "evidence_post_id": "00000000-0000-0000-0000-000000000001",
                        "observed_at": datetime(2026, 8, 1, 9, tzinfo=UTC),
                        "time_axis_code": "event_occurred_at",
                        "is_missing": False,
                    },
                    {
                        "post_id": "00000000-0000-0000-0000-000000000001",
                        "case_kind_code": "claim_investigation",
                        "milestone_type_code": "cause_confirmed",
                        "evidence_text": None,
                        "evidence_post_id": None,
                        "observed_at": None,
                        "time_axis_code": None,
                        "is_missing": True,
                    },
                ]
            return await super().fetch(query, *args)

    result = await fetch_operations_dashboard(OpenConnection(), [])

    lifecycle = result["cases"][0]["lifecycles"][0]
    assert lifecycle["status_code"] == "open"
    assert lifecycle["elapsed_seconds"] is None
    assert result["lifecycle_metrics"][0]["open_case_count"] == 1


@pytest.fixture
def anyio_backend() -> str:
    """Use the installed asyncio backend for async projection tests."""
    return "asyncio"
