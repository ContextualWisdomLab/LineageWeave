"""Contracts for the durable post-content queue boundary."""

from __future__ import annotations

import asyncio
import re
from pathlib import Path

from backend.app.post_content_queue import (
    FAILED,
    POST_CONTENT_STREAM_KEY,
    QUEUED,
    RUNNING,
    SUCCEEDED,
    post_content_api_status,
    post_content_is_complete,
    post_content_stream_fields,
    source_body_sha256,
)

_ROOT = Path(__file__).resolve().parents[1]


def test_stream_is_a_wakeup_and_never_contains_a_body() -> None:
    fields = post_content_stream_fields(
        post_id="00000000-0000-0000-0000-000000000001",
        source_body_digest="ab" * 32,
    )
    assert POST_CONTENT_STREAM_KEY == "post-content-ingestion"
    assert set(fields) == {"post_id", "source_body_sha256"}
    assert "body" not in fields.values()
    assert source_body_sha256("body") == source_body_sha256("body")
    assert source_body_sha256("body") != source_body_sha256("changed")


def test_api_status_does_not_call_failed_content_ready() -> None:
    assert post_content_api_status(QUEUED, content_present=False) == "processing"
    assert post_content_api_status(QUEUED, content_present=True) == "processing"
    assert post_content_api_status(RUNNING, content_present=False) == "processing"
    assert post_content_api_status(SUCCEEDED, content_present=True) == "ready"
    assert post_content_api_status(FAILED, content_present=False) == "unavailable"
    assert post_content_api_status(FAILED, content_present=True) == "unavailable"


def test_embedding_gap_is_not_complete_content() -> None:
    class FakeConnection:
        async def fetchval(self, query: str, *_args: object) -> int:
            assert "post_content_embedding" in query
            assert "post_content_image_region_embedding" in query
            assert "unit_kind_code <> 'image'" in query
            return 0

    assert (
        asyncio.run(
            post_content_is_complete(
                FakeConnection(),
                "00000000-0000-0000-0000-000000000001",
                embedding_model_code="text-embedding-3-large",
            )
        )
        is False
    )


def test_structure_gap_is_part_of_orchestrated_completeness() -> None:
    class FakeConnection:
        async def fetchval(self, query: str, *_args: object) -> int:
            assert "post_content_unit_structure" in query
            assert "decision_source_code = 'unresolved'" in query
            return 0

    assert (
        asyncio.run(
            post_content_is_complete(
                FakeConnection(),
                "00000000-0000-0000-0000-000000000001",
                embedding_model_code="text-embedding-3-large",
                require_structure=True,
            )
        )
        is False
    )


def test_republish_query_recovers_only_stale_running_leases() -> None:
    from backend.app import post_content_queue

    class FakeConnection:
        async def fetch(self, query: str, *args: object):
            assert "status_code = $1" in query
            assert "status_code = $2" in query
            assert "started_at < now() - $3::interval" in query
            assert args[0] == QUEUED
            assert args[1] == RUNNING
            return [
                {
                    "post_id": "00000000-0000-0000-0000-000000000001",
                    "source_body_sha256": "a" * 64,
                }
            ]

    class Acquire:
        async def __aenter__(self):
            return FakeConnection()

        async def __aexit__(self, *_args: object) -> None:
            return None

    class Pool:
        def acquire(self):
            return Acquire()

    class Client:
        pass

    published: list[tuple[str, str]] = []

    async def publish(_client, *, post_id: str, source_body_digest: str) -> bool:
        published.append((post_id, source_body_digest))
        return True

    original = post_content_queue.publish_post_content_event
    post_content_queue.publish_post_content_event = publish
    try:
        assert asyncio.run(
            post_content_queue.republish_queued_post_content_jobs(Client(), Pool())
        ) == 1
    finally:
        post_content_queue.publish_post_content_event = original
    assert published == [("00000000-0000-0000-0000-000000000001", "a" * 64)]


def test_existing_units_are_requeued_when_the_source_digest_changes() -> None:
    from backend.app.post_content_queue import ensure_post_content_job

    class FakeConnection:
        def __init__(self) -> None:
            self.executed: list[tuple[str, tuple[object, ...]]] = []

        async def fetchrow(self, _query: str, _post_id: str):
            return {
                "source_body_sha256": source_body_sha256("old body"),
                "status_code": SUCCEEDED,
            }

        async def fetchval(self, _query: str, _post_id: str) -> int:
            return 0

        async def execute(self, query: str, *args: object):
            self.executed.append((query, args))

    conn = FakeConnection()
    job = asyncio.run(
        ensure_post_content_job(
            conn,
            "00000000-0000-0000-0000-000000000001",
            "new body",
            content_complete=True,
        )
    )

    assert job.status_code == QUEUED
    assert job.should_publish is True
    assert any("set source_body_sha256" in query for query, _args in conn.executed)


def test_existing_units_register_as_succeeded_without_a_wakeup() -> None:
    from backend.app.post_content_queue import ensure_post_content_job

    class FakeConnection:
        def __init__(self) -> None:
            self.executed: list[tuple[str, tuple[object, ...]]] = []

        async def fetchrow(self, _query: str, _post_id: str):
            return None

        async def fetchval(self, _query: str, _post_id: str) -> int:
            return 0

        async def execute(self, query: str, *args: object):
            self.executed.append((query, args))

    conn = FakeConnection()
    job = asyncio.run(
        ensure_post_content_job(
            conn,
            "00000000-0000-0000-0000-000000000001",
            "existing body",
            content_complete=True,
        )
    )

    assert job.status_code == SUCCEEDED
    assert job.should_publish is False
    assert any("insert into post_content_ingestion_job" in query for query, _args in conn.executed)


def test_migration_contains_normalized_job_and_status_event_tables() -> None:
    migration = (_ROOT / "migrations" / "0050_post_content_ingestion_queue.sql").read_text()
    assert "create table if not exists post_content_ingestion_job" in migration
    assert "create table if not exists post_content_ingestion_job_status_event" in migration
    assert "post_body" not in migration
    assert "jsonb" not in migration.casefold()
    for table_name in re.findall(r"create table if not exists\s+([a-z0-9_]+)", migration):
        assert len(table_name.split("_")) >= 2


def test_migration_replay_window_includes_post_content_queue() -> None:
    migrate = (_ROOT / "docker/postgres-init/migrate.sh").read_text()
    assert "0050_*)" in migrate
