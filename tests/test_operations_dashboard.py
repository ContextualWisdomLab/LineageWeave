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
        return {
            "total_post_count": 4,
            "total_event_count": 3,
            "external_post_count": 1,
            "pending_analysis_count": 1,
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
                    "fact_ordinal": 0,
                }
            ]
        return [
            {
                "post_id": "00000000-0000-0000-0000-000000000001",
                "case_kind_code": "claim_investigation",
                "summary_text": "원인 수주가 연결됨",
                "evidence_text": "Synthetic cited sentence",
                "project_name": "Synthetic Project",
                "occurred_at": datetime(2026, 8, 12, tzinfo=timezone.utc),
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
    assert result["cases"] == [
        {
            "post_id": "00000000-0000-0000-0000-000000000001",
            "case_kind_code": "claim_investigation",
            "case_kind_label": "클레임 원인 규명",
            "project_name": "Synthetic Project",
            "summary_text": "원인 수주가 연결됨",
            "evidence_text": "Synthetic cited sentence",
            "occurred_at": "2026-08-12T00:00:00+00:00",
            "facts": [
                {
                    "fact_type_code": "originating_order",
                    "fact_type_label": "원인 수주",
                    "value_text": "Synthetic order 7",
                    "evidence_text": "Synthetic cited sentence",
                }
            ],
        }
    ]
    assert len(conn.queries) == 3
    for query, args in conn.queries:
        assert "visibility_code = 'public'" in query
        assert "corporate_entity_id::text = any($1::text[])" in query
        assert "process_unit_id::text = any($2::text[])" in query
        assert "coalesce(post.event_occurred_at, post.created_at)" in query
        assert args[1:] == (["00000000-0000-0000-0000-000000000008"], date(2026, 8, 1), date(2026, 8, 31))


@pytest.mark.anyio
async def test_dashboard_zero_denominator_and_invalid_period() -> None:
    """An empty corpus has 0%, while an inverted interval fails closed."""

    class EmptyConnection(_Connection):
        async def fetchrow(self, query: str, *args: object) -> dict[str, int]:
            self.queries.append((query, args))
            return dict.fromkeys(
                ("total_post_count", "total_event_count", "external_post_count", "pending_analysis_count"),
                0,
            )

        async def fetch(self, query: str, *args: object) -> list[dict[str, object]]:
            self.queries.append((query, args))
            return []

    assert (await fetch_operations_dashboard(EmptyConnection(), []))["external_percent"] == 0.0
    with pytest.raises(ValueError, match="period_start"):
        await fetch_operations_dashboard(
            EmptyConnection(), [], [], date(2026, 9, 1), date(2026, 8, 31)
        )


@pytest.fixture
def anyio_backend() -> str:
    """Use the installed asyncio backend for async projection tests."""
    return "asyncio"
