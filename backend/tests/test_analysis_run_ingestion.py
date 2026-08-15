"""Repository tests that exercise every provenance transaction branch."""

from __future__ import annotations

import asyncio
from collections import deque
from datetime import datetime, timedelta, timezone
from typing import Any

import pytest

from backend.app.analysis_run_ingestion import (
    AnalysisRunConflict,
    complete_analysis_run,
    list_analysis_run_summaries,
    register_analysis_run,
)
from lineageweave.analysis_run import (
    AnalysisRunConfiguration,
    AnalysisRunRegistration,
    SourceProfileReference,
    SourceSnapshotEvidence,
)

UTC = timezone.utc
DIGEST_A = "a" * 64
DIGEST_B = "b" * 64


class FakeTransaction:
    """Record transaction entry/exit without a database dependency."""

    def __init__(self, owner: "FakeConnection") -> None:
        self.owner = owner

    async def __aenter__(self) -> "FakeTransaction":
        self.owner.transaction_entries += 1
        return self

    async def __aexit__(self, exc_type: Any, exc: Any, traceback: Any) -> bool:
        self.owner.transaction_exits.append(exc_type)
        return False


class FakeConnection:
    """Queue deterministic rows and retain every SQL call for assertions."""

    def __init__(
        self,
        *,
        fetchrows: list[dict[str, Any] | None] | None = None,
        fetches: list[list[dict[str, Any]]] | None = None,
    ) -> None:
        self.fetchrow_results = deque(fetchrows or [])
        self.fetch_results = deque(fetches or [])
        self.calls: list[tuple[str, str, tuple[Any, ...]]] = []
        self.transaction_entries = 0
        self.transaction_exits: list[Any] = []

    def transaction(self) -> FakeTransaction:
        return FakeTransaction(self)

    async def fetchrow(self, query: str, *arguments: Any) -> dict[str, Any] | None:
        self.calls.append(("fetchrow", query, arguments))
        return self.fetchrow_results.popleft()

    async def fetch(self, query: str, *arguments: Any) -> list[dict[str, Any]]:
        self.calls.append(("fetch", query, arguments))
        return self.fetch_results.popleft()

    async def execute(self, query: str, *arguments: Any) -> str:
        self.calls.append(("execute", query, arguments))
        return "INSERT 0 1"


def _inputs() -> tuple[
    SourceProfileReference,
    SourceSnapshotEvidence,
    AnalysisRunConfiguration,
    datetime,
]:
    started = datetime(2026, 8, 15, 1, 0, tzinfo=UTC)
    return (
        SourceProfileReference("configured-primary", 1, DIGEST_A),
        SourceSnapshotEvidence(
            DIGEST_B,
            started,
            started - timedelta(minutes=1),
            12,
            10,
            8,
        ),
        AnalysisRunConfiguration(0, True, True, True, "tepp-v1", "aggregate"),
        started,
    )


def test_register_analysis_run_is_one_idempotent_transaction() -> None:
    profile, snapshot, configuration, started = _inputs()
    conn = FakeConnection(
        fetchrows=[
            {"source_profile_id": "profile-id"},
            {"source_snapshot_id": "snapshot-id"},
            {"analysis_run_id": "run-id"},
        ]
    )
    result = asyncio.run(
        register_analysis_run(
            conn,
            registration=AnalysisRunRegistration("account-id", "run-key", started),
            profile=profile,
            snapshot=snapshot,
            configuration=configuration,
        )
    )
    assert result == "run-id"
    assert conn.transaction_entries == 1
    assert conn.transaction_exits == [None]
    assert [call[0] for call in conn.calls] == [
        "fetchrow",
        "fetchrow",
        "fetchrow",
        "execute",
        "execute",
    ]
    all_sql = "\n".join(call[1] for call in conn.calls).lower()
    assert "source sql" not in all_sql
    assert "dsn" not in all_sql


@pytest.mark.parametrize(
    ("rows", "message", "expected_calls"),
    [
        ([None], "source profile", 1),
        ([{"source_profile_id": "p"}, None], "source snapshot", 2),
        (
            [
                {"source_profile_id": "p"},
                {"source_snapshot_id": "s"},
                None,
            ],
            "idempotency key",
            3,
        ),
    ],
)
def test_register_analysis_run_fails_closed_on_immutable_conflicts(
    rows: list[dict[str, Any] | None], message: str, expected_calls: int
) -> None:
    profile, snapshot, configuration, started = _inputs()
    conn = FakeConnection(fetchrows=rows)
    with pytest.raises(AnalysisRunConflict, match=message):
        asyncio.run(
            register_analysis_run(
                conn,
                registration=AnalysisRunRegistration("account-id", "run-key", started),
                profile=profile,
                snapshot=snapshot,
                configuration=configuration,
            )
        )
    assert len(conn.calls) == expected_calls
    assert conn.transaction_exits == [AnalysisRunConflict]


@pytest.mark.parametrize(
    ("succeeded", "status_code", "event_code"),
    [
        (True, "analysis_run_succeeded", "analysis_run_completed_event"),
        (False, "analysis_run_failed", "analysis_run_failed_event"),
    ],
)
def test_complete_analysis_run_records_terminal_status_and_event(
    succeeded: bool, status_code: str, event_code: str
) -> None:
    conn = FakeConnection(fetchrows=[{"request_digest_sha256": DIGEST_A}])
    completed = datetime(2026, 8, 15, 2, 0, tzinfo=UTC)
    asyncio.run(
        complete_analysis_run(
            conn,
            analysis_run_id="run-id",
            actor_account_id="account-id",
            succeeded=succeeded,
            completed_at=completed,
        )
    )
    assert conn.calls[0][2][1] == status_code
    assert conn.calls[1][2][1] == event_code
    assert conn.transaction_exits == [None]


def test_complete_analysis_run_rejects_missing_or_completed_run() -> None:
    conn = FakeConnection(fetchrows=[None])
    with pytest.raises(AnalysisRunConflict, match="missing or already completed"):
        asyncio.run(
            complete_analysis_run(
                conn,
                analysis_run_id="run-id",
                actor_account_id="account-id",
                succeeded=True,
                completed_at=datetime(2026, 8, 15, 2, 0, tzinfo=UTC),
            )
        )
    assert conn.transaction_exits == [AnalysisRunConflict]


def test_list_analysis_runs_serializes_only_safe_aggregate_fields() -> None:
    started = datetime(2026, 8, 15, 1, 0, tzinfo=UTC)
    conn = FakeConnection(
        fetches=[
            [
                {
                    "analysis_run_id": "run-id",
                    "source_profile_key": "configured-primary",
                    "profile_revision": 1,
                    "run_status_code": "analysis_run_succeeded",
                    "request_digest_sha256": DIGEST_A,
                    "source_digest_sha256": DIGEST_B,
                    "knowledge_cutoff": started,
                    "maximum_available_time": started - timedelta(minutes=1),
                    "row_count": 12,
                    "document_count": 10,
                    "thread_count": 8,
                    "started_at": started,
                    "completed_at": started + timedelta(minutes=2),
                    "row_limit": 0,
                    "write_reports": True,
                    "inspect_inline_images": True,
                    "validate_runtime_schema": True,
                    "model_contract_version": "tepp-v1",
                    "output_profile": "aggregate",
                }
            ]
        ]
    )
    result = asyncio.run(list_analysis_run_summaries(conn, limit=25))
    assert result[0]["source_snapshot"]["row_count"] == 12
    assert conn.calls[0][2] == (25,)
    serialized = str(result).lower()
    for forbidden in ("dsn", "source_table", "query_text", "raw_content"):
        assert forbidden not in serialized


@pytest.mark.parametrize("limit", [0, 101, True, 1.5])
def test_list_analysis_runs_rejects_invalid_limits(limit: object) -> None:
    with pytest.raises(ValueError, match="1 through 100"):
        asyncio.run(list_analysis_run_summaries(FakeConnection(), limit=limit))  # type: ignore[arg-type]
