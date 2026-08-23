"""Contracts for the durable post-content queue boundary."""

from __future__ import annotations

import asyncio
import re
from datetime import timedelta
from pathlib import Path

import pytest

from backend.app.post_content_queue import (
    FAILED,
    POST_CONTENT_RETRY_INTERVAL,
    POST_CONTENT_STREAM_KEY,
    QUEUED,
    RUNNING,
    STALE_RUNNING_INTERVAL,
    SUCCEEDED,
    fetch_post_summary_source,
    post_body_has_images,
    post_content_api_status,
    post_content_is_complete,
    post_content_stream_fields,
    post_content_summary_is_ready,
    post_content_summary_status_message,
    record_post_content_backfill_success,
    requeue_failed_post_content_job,
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


def test_summary_status_distinguishes_terminal_image_failure_from_processing() -> None:
    assert "ingestion failed" in post_content_summary_status_message(FAILED)
    assert "still being processed" in post_content_summary_status_message(QUEUED)
    assert "still being processed" in post_content_summary_status_message(RUNNING)


def test_adrs_keep_post_open_separate_from_image_summary_readiness() -> None:
    semantic_contract = (
        _ROOT / "docs/adr/0052-plain-orchestrator-semantic-evidence.md"
    ).read_text()
    ingestion_contract = (
        _ROOT / "docs/adr/0098-valkey-backed-post-content-ingestion.md"
    ).read_text()
    stale_contract = (
        _ROOT / "docs/adr/0114-stale-summary-buyer-continuity.md"
    ).read_text()
    semantic_contract = " ".join(semantic_contract.split())
    ingestion_contract = " ".join(ingestion_contract.split())
    stale_contract = " ".join(stale_contract.split())

    assert "Source-post open and source rendering" in semantic_contract
    assert "withholds both current and stale persisted summaries" in semantic_contract
    assert "never blocks source-post open or source" in ingestion_contract
    assert "MUST NOT call VISION directly" in ingestion_contract
    assert "image-bearing stale summary is" in stale_contract
    assert "normalized summary-input SHA-256" in semantic_contract
    assert "durable job row to match the current raw-body SHA-256" in ingestion_contract
    assert "Legacy rows with no input binding are never current" in stale_contract


def test_summary_waits_for_image_evidence_and_detects_images_without_body_logging() -> None:
    class FakeConnection:
        async def fetchval(self, query: str, *args: object) -> int:
            assert "post_content_ingestion_job" in query
            assert "job.source_body_sha256 = $2" in query
            assert "job.status_code = $3" in query
            assert "post_content_image" in query
            assert "description_status_code <> 'described'" in query
            assert args == (
                "00000000-0000-0000-0000-000000000001",
                "ab" * 32,
                SUCCEEDED,
            )
            return 0

    assert post_body_has_images(
        "<p>본문</p><img src='data:image/png;base64,iVBORw0KGgo='>"
    ) is True
    assert post_body_has_images("본문만 있습니다.") is False
    assert (
        asyncio.run(
            post_content_summary_is_ready(
                FakeConnection(),
                "00000000-0000-0000-0000-000000000001",
                "ab" * 32,
            )
        )
        is False
    )


def test_summary_input_binding_migration_is_wired_for_every_database_path() -> None:
    migration = (_ROOT / "migrations/0139_post_summary_input_binding.sql").read_text()
    rollback = (
        _ROOT / "migrations/rollback/0139_post_summary_input_binding.sql"
    ).read_text()
    initial = (_ROOT / "migrations/0001_initial_schema.sql").read_text()
    standalone = (_ROOT / "migrations/0008_post_summary_result.sql").read_text()
    replay = (_ROOT / "docker/postgres-init/migrate.sh").read_text()
    seed = (_ROOT / "scripts/seed_demo_data.py").read_text()

    assert "add column if not exists summary_input_sha256" in migration
    assert "post_summary_result_summary_input_sha256_check" in migration
    assert "drop column if exists summary_input_sha256" in rollback
    assert "summary_input_sha256 text" in initial
    assert "summary_input_sha256 text" in standalone
    assert "0139_*" in replay
    assert "0139_post_summary_input_binding.sql" in seed


def test_summary_source_orders_parent_and_region_vision_evidence() -> None:
    class FakeConnection:
        async def fetch(self, query: str, post_id: str) -> list[dict[str, object]]:
            assert "post_content_image_region" in query
            assert "order by unit.unit_index, region.region_index" in query
            return [
                {
                    "unit_index": 0,
                    "unit_text": "Synthetic paragraph.",
                    "region_index": None,
                    "extracted_text": None,
                    "image_caption": None,
                },
                {
                    "unit_index": 1,
                    "unit_text": "[image: Synthetic parent caption.]",
                    "region_index": 0,
                    "extracted_text": "Synthetic table header",
                    "image_caption": "Synthetic upper region.",
                },
                {
                    "unit_index": 1,
                    "unit_text": "[image: Synthetic parent caption.]",
                    "region_index": 1,
                    "extracted_text": "Synthetic table row",
                    "image_caption": "Synthetic lower region.",
                },
            ]

    source = asyncio.run(fetch_post_summary_source(FakeConnection(), "synthetic-post"))

    assert source == (
        "Synthetic paragraph.\n\n"
        "[image: Synthetic parent caption.]\n\n"
        "[image region 0]\nSynthetic upper region.\nSynthetic table header\n\n"
        "[image region 1]\nSynthetic lower region.\nSynthetic table row"
    )


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


def test_image_vision_gap_is_not_complete_content() -> None:
    class FakeConnection:
        async def fetchval(self, query: str, *_args: object) -> int:
            assert "post_content_image" in query
            assert "image.description_status_code <> 'described'" in query
            assert "post_content_image_region" in query
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


def test_republish_query_recovers_due_queue_and_stale_running_leases() -> None:
    from backend.app import post_content_queue

    class FakeConnection:
        async def fetch(self, query: str, *args: object):
            assert "status_code = $1" in query
            assert "status_code = $3" in query
            assert "join source_post post" in query
            assert "source_detail_state_code" in query
            assert "coalesce(upper(btrim(post.source_detail_state_code)), '') <> 'W'" in query
            assert "started_at < now() - $4::interval" in query
            assert args[0] == QUEUED
            assert args[2] == RUNNING
            assert args[1] == POST_CONTENT_RETRY_INTERVAL
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


def test_preledger_units_cannot_register_current_digest_as_succeeded() -> None:
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

    assert job.status_code == QUEUED
    assert job.should_publish is True
    assert any("insert into post_content_ingestion_job" in query for query, _args in conn.executed)


def test_failed_same_body_is_not_requeued_by_a_read_poll() -> None:
    from backend.app.post_content_queue import ensure_post_content_job

    class FakeConnection:
        async def fetchrow(self, _query: str, _post_id: str):
            return {
                "source_body_sha256": source_body_sha256("same body"),
                "status_code": FAILED,
            }

        async def fetchval(self, _query: str, _post_id: str) -> int:
            return 0

        async def execute(self, *_args: object) -> None:
            raise AssertionError("a failed job must remain terminal for the same digest")

    job = asyncio.run(
        ensure_post_content_job(
            FakeConnection(),
            "00000000-0000-0000-0000-000000000001",
            "same body",
            content_complete=False,
        )
    )

    assert job.status_code == FAILED
    assert job.should_publish is False


def test_changed_body_starts_a_retry_cycle_without_reusing_claim_identity() -> None:
    from backend.app.post_content_queue import ensure_post_content_job

    class FakeConnection:
        def __init__(self) -> None:
            self.executed: list[tuple[str, tuple[object, ...]]] = []

        async def fetchrow(self, _query: str, _post_id: str):
            return {
                "source_body_sha256": source_body_sha256("old body"),
                "status_code": FAILED,
            }

        async def fetchval(self, _query: str, _post_id: str) -> int:
            return 0

        async def execute(self, query: str, *args: object) -> None:
            self.executed.append((query, args))

    conn = FakeConnection()
    job = asyncio.run(
        ensure_post_content_job(
            conn,
            "00000000-0000-0000-0000-000000000001",
            "new body",
            content_complete=False,
        )
    )

    assert job.status_code == QUEUED
    assert job.should_publish is True
    assert not any("attempt_count = 0" in query for query, _args in conn.executed)


def test_recovery_query_carries_one_bounded_retry_interval() -> None:
    assert POST_CONTENT_RETRY_INTERVAL == timedelta(minutes=5)
    migration = (_ROOT / "migrations" / "0050_post_content_ingestion_queue.sql").read_text()
    assert "queued_at timestamptz not null" in migration


def test_explicit_retry_requeues_only_one_failed_job_without_reusing_claim_identity() -> None:
    executed: list[tuple[str, tuple[object, ...]]] = []

    class FakeConnection:
        async def fetchrow(self, query: str, *_args: object):
            assert "for update" in query
            if "from source_post" in query:
                return {"post_body": "current body"}
            return {"status_code": FAILED}

        async def fetchval(self, query: str, *_args: object) -> int:
            assert "status_ordinal" in query
            return 4

        async def execute(self, query: str, *args: object) -> str:
            executed.append((query, args))
            return "UPDATE 1" if query.lstrip().startswith("update") else "INSERT 0 1"

    request = asyncio.run(
        requeue_failed_post_content_job(
            FakeConnection(),
            "00000000-0000-0000-0000-000000000001",
            "current body",
        )
    )

    assert request.status_code == QUEUED
    assert request.should_publish is True
    assert request.source_body_sha256 == source_body_sha256("current body")
    assert len(executed) == 2
    assert "attempt_count = 0" not in executed[0][0]
    assert executed[1][1][-1] == "operator requested an explicit post-content retry"


def test_explicit_retry_rejects_missing_and_nonterminal_jobs() -> None:
    """The operator command cannot create a job or reset an active job."""

    class MissingConnection:
        async def fetchrow(self, _query: str, *_args: object):
            return None

    with pytest.raises(ValueError, match="does not exist"):
        asyncio.run(
            requeue_failed_post_content_job(
                MissingConnection(),
                "00000000-0000-0000-0000-000000000001",
                "current body",
            )
        )

    class QueuedConnection:
        async def fetchrow(self, _query: str, *_args: object):
            return {"status_code": QUEUED}

    with pytest.raises(ValueError, match="only a failed"):
        asyncio.run(
            requeue_failed_post_content_job(
                QueuedConnection(),
                "00000000-0000-0000-0000-000000000001",
                "current body",
            )
        )


def test_backfill_success_clears_terminal_error_and_records_succeeded() -> None:
    executed: list[tuple[str, tuple[object, ...]]] = []

    class FakeConnection:
        async def fetchrow(self, query: str, *_args: object):
            assert "for update" in query
            if "from source_post" in query:
                return {"post_body": "current body"}
            return {"status_code": FAILED}

        async def fetchval(self, query: str, *_args: object) -> int:
            assert "status_ordinal" in query
            return 5

        async def execute(self, query: str, *args: object) -> str:
            executed.append((query, args))
            return "UPDATE 1" if query.lstrip().startswith("update") else "INSERT 0 1"

    request = asyncio.run(
        record_post_content_backfill_success(
            FakeConnection(),
            "00000000-0000-0000-0000-000000000001",
            "current body",
        )
    )

    assert request.status_code == SUCCEEDED
    assert request.should_publish is False
    assert len(executed) == 2
    assert "last_error_code = null" in executed[0][0]
    assert executed[1][1][-1] == "operator backfill persisted post-content evidence"


def test_backfill_success_rejects_a_source_revision_after_provider_work() -> None:
    class FakeConnection:
        async def fetchrow(self, query: str, *_args: object):
            if "from source_post" in query:
                return {"post_body": "newer body"}
            return {"status_code": FAILED}

        async def execute(self, *_args: object) -> None:
            raise AssertionError("a stale backfill must not update the ledger")

    with pytest.raises(ValueError, match="source body changed"):
        asyncio.run(
            record_post_content_backfill_success(
                FakeConnection(),
                "00000000-0000-0000-0000-000000000001",
                "older body",
            )
        )


def test_recovery_republishes_due_rows_in_queued_at_order() -> None:
    from contextlib import asynccontextmanager

    from backend.app.post_content_queue import republish_queued_post_content_jobs

    class FakeConnection:
        def __init__(self) -> None:
            self.query = ""
            self.args: tuple[object, ...] = ()

        async def fetch(self, query: str, *args: object):
            self.query = query
            self.args = args
            return [
                {"post_id": "first", "source_body_sha256": "a" * 64},
                {"post_id": "second", "source_body_sha256": "b" * 64},
            ]

    class FakePool:
        def __init__(self, connection: FakeConnection) -> None:
            self.connection = connection

        @asynccontextmanager
        async def acquire(self):
            yield self.connection

    class FakeClient:
        def __init__(self) -> None:
            self.events: list[tuple[str, str]] = []

        async def xadd(self, _stream: str, fields: dict[str, str], **_kwargs: object) -> str:
            self.events.append((fields["post_id"], fields["source_body_sha256"]))
            return str(len(self.events))

    connection = FakeConnection()
    client = FakeClient()
    published = asyncio.run(
        republish_queued_post_content_jobs(client, FakePool(connection), limit=2)
    )

    assert published == 2
    assert client.events == [("first", "a" * 64), ("second", "b" * 64)]
    assert "queued_at <= now() - $2::interval" in connection.query
    assert "coalesce(upper(btrim(post.source_detail_state_code)), '') <> 'W'" in connection.query
    assert "order by post_content_ingestion_job.queued_at" in connection.query
    assert connection.args == (QUEUED, POST_CONTENT_RETRY_INTERVAL, RUNNING, STALE_RUNNING_INTERVAL, 2)


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


def test_claim_identity_is_never_reset_by_queue_transitions() -> None:
    source = (_ROOT / "backend/app/post_content_queue.py").read_text()
    assert "attempt_count = 0" not in source
    assert "attempt_count = attempt_count + 1" not in source
