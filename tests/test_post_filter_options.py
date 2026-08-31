"""Unit tests for the authorized post-filter projection."""

from __future__ import annotations

import asyncio
from typing import Any

from backend.app.main import _post_filter_options, _post_list_query_plan


class _RecordingConnection:
    """Return synthetic option rows while recording database round trips."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, tuple[Any, ...]]] = []

    async def fetch(self, query: str, *args: Any) -> list[dict[str, object]]:
        """Record the closed query and return both supported option categories."""
        self.calls.append((query, args))
        selected_total = None if len(args[2]) > 1 else (2 if args[2] or args[3] else 4)
        return [
            {
                "visibility_code": "public",
                "total_eligible": 3,
                "voice_codes": ["voc"],
                "labels": {"public": "Public", "private": "Private", "voc": "Voice of Customer"},
                "display_orders": {"public": 1, "private": 2, "voc": 1},
                "source_context_required": True,
                "voice_catalog": [{"code": "voc", "label": "Voice of Customer"}],
                "selected_total_count": selected_total,
            },
            {
                "visibility_code": "private",
                "total_eligible": 1,
                "voice_codes": ["voc"],
                "labels": {"public": "Public", "private": "Private", "voc": "Voice of Customer"},
                "display_orders": {"public": 1, "private": 2, "voc": 1},
                "source_context_required": True,
                "voice_catalog": [{"code": "voc", "label": "Voice of Customer"}],
                "selected_total_count": selected_total,
            },
        ]


class _RecordingTransaction:
    """Record entry/exit for the transaction-local plan policy."""

    def __init__(self, events: list[str]) -> None:
        self.events = events

    async def __aenter__(self) -> None:
        """Record transaction entry."""
        self.events.append("begin")

    async def __aexit__(self, *args: object) -> None:
        """Record transaction exit."""
        self.events.append("end")


class _PlanConnection:
    """Minimal connection double for the default-list plan boundary."""

    def __init__(self) -> None:
        self.events: list[str] = []

    def transaction(self) -> _RecordingTransaction:
        """Return the recording transaction context."""
        return _RecordingTransaction(self.events)

    async def execute(self, statement: str) -> None:
        """Record the exact local setting."""
        self.events.append(statement)


def test_post_filter_options_use_one_authorized_source_scan() -> None:
    """Both complete option lists share one parameterized ABAC-filtered query."""
    conn = _RecordingConnection()

    voc_types, visibilities, total_count, source_context_required, labels, catalog = asyncio.run(
        _post_filter_options(
            conn,
            frozenset({"corp-a"}),
            frozenset({"pu-a"}),
        )
    )

    assert voc_types == [{"code": "voc", "label": "Voice of Customer"}]
    assert visibilities == [
        {"code": "public", "label": "Public"},
        {"code": "private", "label": "Private"},
    ]
    assert total_count == 4
    assert source_context_required is True
    assert labels["public"] == "Public"
    assert catalog == [{"code": "voc", "label": "Voice of Customer"}]
    assert len(conn.calls) == 1
    query, args = conn.calls[0]
    assert "voice_taxonomy_day_read_projection" in query
    assert "scope.corporate_entity_id = any($1::uuid[])" in query
    assert "scope.process_unit_key = any($2::uuid[])" in query
    assert "scope.source_context_present = mode.source_context_required" in query
    assert args == (["corp-a"], ["pu-a"], [], None)


def test_default_post_list_custom_plan_is_transaction_local() -> None:
    """Only the unfiltered list gets the measured custom-plan exception."""
    default_conn = _PlanConnection()

    async def exercise_default() -> None:
        async with _post_list_query_plan(default_conn, default_population=True):
            default_conn.events.append("query")

    asyncio.run(exercise_default())
    assert default_conn.events == [
        "begin",
        "set local plan_cache_mode = 'force_custom_plan'",
        "query",
        "end",
    ]

    filtered_conn = _PlanConnection()

    async def exercise_filtered() -> None:
        async with _post_list_query_plan(filtered_conn, default_population=False):
            filtered_conn.events.append("query")

    asyncio.run(exercise_filtered())
    assert filtered_conn.events == ["query"]


def test_filter_projection_returns_exact_single_category_count_only() -> None:
    """A multi-Voice union stays unprojected because memberships overlap."""
    single = _RecordingConnection()
    result = asyncio.run(
        _post_filter_options(
            single, frozenset({"corp-a"}), frozenset(), ["voc"], "public"
        )
    )
    assert result[2] == 2
    assert single.calls[0][1] == (["corp-a"], [], ["voc"], "public")

    multiple = _RecordingConnection()
    result = asyncio.run(
        _post_filter_options(
            multiple, frozenset({"corp-a"}), frozenset(), ["voc", "vop"], None
        )
    )
    assert result[2] is None
