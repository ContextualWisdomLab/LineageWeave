"""Contracts for the durable Event Lineage rebuild queue (ADR 0100 / issue #289)."""

from __future__ import annotations

import asyncio
import time
from datetime import datetime
from pathlib import Path
from uuid import uuid4

from lineageweave.adjudication_client import NullAdjudicationClient
from lineageweave.fixtures import sample_records
from lineageweave.models import Record
from lineageweave.reconstruct import DEFAULT_PAIR_LIMIT, estimate_candidate_pairs

from backend.app.lineage_rebuild_queue import (
    LLM_REQUESTED,
    LLM_SKIPPED,
    LLM_UNAVAILABLE,
    QUEUED,
    LINEAGE_REBUILD_STREAM_KEY,
    adjudication_client_for_job,
    enqueue_lineage_rebuild,
    initial_llm_channel_status,
    lineage_rebuild_stream_fields,
    next_action_copy,
    source_snapshot_sha256,
)

_ROOT = Path(__file__).resolve().parents[1]


class _FakeConnection:
    def __init__(self, existing=None, *, conflict_on_insert: bool = False) -> None:
        self.existing = existing
        self.conflict_on_insert = conflict_on_insert
        self.executed: list[tuple[str, tuple[object, ...]]] = []
        self.inserted = None

    async def fetchrow(self, query: str, *args: object):
        self.executed.append((query, args))
        if "source_snapshot_sha256 = $1" in query:
            return self.existing
        if "insert into lineage_rebuild_job" in query:
            if self.conflict_on_insert:
                return None
            self.inserted = {
                "lineage_rebuild_job_id": uuid4(),
                "requested_by_account_id": args[0],
                "source_snapshot_sha256": args[1],
                "knowledge_cutoff": args[2],
                "pair_estimate": args[3],
                "pair_limit": args[4],
                "llm_channel_requested": args[5],
                "llm_channel_status_code": args[6],
                "status_code": args[7],
                "attempt_count": 0,
                "edge_count": None,
                "result_sha256": None,
                "failure_code": None,
                "queued_at": datetime(2026, 8, 20),
            }
            return self.inserted
        return None

    async def fetchval(self, _query: str, *_args: object) -> int:
        return 0

    async def execute(self, query: str, *args: object):
        self.executed.append((query, args))


class _CountingClient:
    available = True

    def __init__(self) -> None:
        self.calls = 0

    def judge(self, candidate_label: str, record_label: str) -> float:
        self.calls += 1
        time.sleep(0.05)
        return 0.8


def test_stream_is_a_wakeup_and_never_contains_a_body() -> None:
    fields = lineage_rebuild_stream_fields(
        lineage_rebuild_job_id="00000000-0000-0000-0000-000000000001",
    )
    assert LINEAGE_REBUILD_STREAM_KEY == "lineage-rebuild-outbox"
    assert set(fields) == {"lineage_rebuild_job_id"}
    assert "body" not in fields
    digest = source_snapshot_sha256(sample_records(), llm_channel_requested=True)
    changed = source_snapshot_sha256(sample_records(), llm_channel_requested=False)
    assert len(digest) == 64
    assert digest != changed


def test_estimate_never_counts_bodies_or_invents_llm_pairs() -> None:
    records = [
        Record("a", "G", "alpha", datetime(2026, 1, 1, 0), ""),
        Record("b", "G", "beta", datetime(2026, 1, 1, 1), ""),
        Record("c", "G", "gamma", datetime(2026, 1, 1, 2), ""),
    ]
    assert estimate_candidate_pairs(records) == 3
    wide = [Record(f"r{i}", "G", f"row {i}", datetime(2026, 1, 1, i), "") for i in range(6)]
    assert estimate_candidate_pairs(wide, candidate_window=2) == 9


def test_llm_status_is_unavailable_or_skipped_never_zero() -> None:
    assert (
        initial_llm_channel_status(
            llm_channel_requested=True,
            llm_available=False,
            pair_estimate=3,
            pair_limit=DEFAULT_PAIR_LIMIT,
        )
        == LLM_UNAVAILABLE
    )
    assert (
        initial_llm_channel_status(
            llm_channel_requested=True,
            llm_available=True,
            pair_estimate=DEFAULT_PAIR_LIMIT + 1,
            pair_limit=DEFAULT_PAIR_LIMIT,
        )
        == LLM_SKIPPED
    )
    assert (
        initial_llm_channel_status(
            llm_channel_requested=True,
            llm_available=True,
            pair_estimate=3,
            pair_limit=DEFAULT_PAIR_LIMIT,
        )
        == LLM_REQUESTED
    )
    client = adjudication_client_for_job(_CountingClient(), LLM_SKIPPED)
    assert isinstance(client, NullAdjudicationClient)


def test_enqueue_does_not_call_an_llm_and_is_idempotent() -> None:
    client = _CountingClient()
    conn = _FakeConnection()
    first = asyncio.run(
        enqueue_lineage_rebuild(
            conn,
            account_id="00000000-0000-0000-0000-000000000009",
            records=sample_records(),
            llm_channel_requested=True,
            llm_available=True,
        )
    )
    assert first.should_publish is True
    assert first.job["status_code"] == QUEUED
    assert first.job["llm_channel_status_code"] == LLM_REQUESTED
    assert client.calls == 0

    reuse = _FakeConnection(existing=first.job)
    second = asyncio.run(
        enqueue_lineage_rebuild(
            reuse,
            account_id="00000000-0000-0000-0000-000000000009",
            records=sample_records(),
            llm_channel_requested=True,
            llm_available=True,
        )
    )
    assert second.should_publish is False
    assert second.job["lineage_rebuild_job_id"] == first.job["lineage_rebuild_job_id"]
    assert client.calls == 0


def test_enqueue_reuses_the_active_row_after_a_unique_race() -> None:
    first = asyncio.run(
        enqueue_lineage_rebuild(
            _FakeConnection(),
            account_id="00000000-0000-0000-0000-000000000009",
            records=sample_records(),
            llm_channel_requested=True,
            llm_available=True,
        )
    )
    raced = _FakeConnection(existing=first.job, conflict_on_insert=True)

    result = asyncio.run(
        enqueue_lineage_rebuild(
            raced,
            account_id="00000000-0000-0000-0000-000000000009",
            records=sample_records(),
            llm_channel_requested=True,
            llm_available=True,
        )
    )

    assert result.should_publish is False
    assert result.job["lineage_rebuild_job_id"] == first.job["lineage_rebuild_job_id"]


def test_http_path_copy_names_the_next_action() -> None:
    assert "Event Lineage" in next_action_copy(
        status_code=QUEUED, llm_channel_status_code=LLM_REQUESTED
    )
    assert "orchestrator" in next_action_copy(
        status_code="lineage_rebuild_succeeded",
        llm_channel_status_code=LLM_UNAVAILABLE,
    )


def test_migration_contains_normalized_job_tables() -> None:
    migration = (_ROOT / "migrations" / "0053_lineage_rebuild_job.sql").read_text()
    assert "create table if not exists lineage_rebuild_job" in migration
    assert "create table if not exists lineage_rebuild_job_status_event" in migration
    assert "jsonb" not in migration.casefold()
    assert "post_body" not in migration
    assert "theta" not in migration.casefold()


def test_migrate_sh_replays_lineage_rebuild_job_migration() -> None:
    migrate = (_ROOT / "docker/postgres-init/migrate.sh").read_text()
    assert "0053_*" in migrate
