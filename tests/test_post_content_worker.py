"""Worker regressions for bounded, evidence-complete post ingestion."""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import UUID

import pytest

from backend.app import post_content_worker
from backend.app.post_content_queue import (
    FAILED,
    POST_CONTENT_MAX_ATTEMPTS,
    QUEUED,
    RUNNING,
    SUCCEEDED,
)
from lineageweave.http_client import HttpAdmissionDeferred, HttpClientError
from lineageweave.operations_case_analysis import OperationsEvidenceSource
from lineageweave.product_semantics import ProductMention

_PRODUCT_ANALYSIS = post_content_worker._persist_product_analysis_if_needed
_VOICE_CLASSIFICATION = post_content_worker._persist_voice_classification_if_needed


@pytest.fixture(autouse=True)
def _isolate_product_analysis(monkeypatch):
    """Keep legacy worker tests focused on their pre-product responsibility."""
    monkeypatch.setattr(
        post_content_worker,
        "_persist_product_analysis_if_needed",
        lambda *_args, **_kwargs: asyncio.sleep(0),
    )
    monkeypatch.setattr(
        post_content_worker,
        "_persist_voice_classification_if_needed",
        lambda *_args, **_kwargs: asyncio.sleep(0),
    )


class _Transaction:
    async def __aenter__(self):
        return self

    async def __aexit__(self, *_args: object) -> bool:
        return False


class _Connection:
    def __init__(self, row: dict[str, object] | None = None, values: list[object] | None = None):
        self.row = row
        self.values = list(values or [])
        self.executed: list[tuple[str, tuple[object, ...]]] = []
        self.fetched: list[tuple[str, tuple[object, ...]]] = []

    def transaction(self) -> _Transaction:
        return _Transaction()

    async def fetchrow(self, *_args: object):
        return self.row

    async def fetch(self, query: str, *args: object):
        self.fetched.append((query, args))
        return []

    async def fetchval(self, query: str, *_args: object):
        if self.values:
            return self.values.pop(0)
        if "status_ordinal" in query:
            return 0
        return False

    async def execute(self, query: str, *args: object) -> str:
        self.executed.append((query, args))
        return "OK"


class _Pool:
    def __init__(self, connection: _Connection):
        self.connection = connection

    @asynccontextmanager
    async def acquire(self):
        yield self.connection


def _row(status: str, attempt_count: int, *, started_at: object = None) -> dict[str, object]:
    return {
        "job_status_code": status,
        "job_attempt_count": attempt_count,
        "job_started_at": started_at,
        "job_queued_at": "queued-at",
        "job_next_attempt_at": None,
        "post_body": "A synthetic post body with a retrieval unit.",
        "post_title": "Synthetic post title",
    }


def test_worker_starts_after_historical_stream_tail() -> None:
    class Client:
        async def xrevrange(self, key: str, *, count: int):
            assert key == post_content_worker.POST_CONTENT_STREAM_KEY
            assert count == 1
            return [("123-0", {})]

    assert asyncio.run(post_content_worker._stream_tail(Client())) == "123-0"


def test_operations_sources_apply_focal_entity_and_process_scope(monkeypatch) -> None:
    """Private linked evidence outside the focal PU never reaches the orchestrator."""
    decisions: list[bool] = []

    async def gather(_conn, _post_id, can_see, _vision):
        decisions.extend(
            can_see(row)
            for row in (
                {"visibility_code": "private", "corporate_entity_id": "corp", "process_unit_id": "pu"},
                {"visibility_code": "private", "corporate_entity_id": "corp", "process_unit_id": "other"},
                {"visibility_code": "private", "corporate_entity_id": "other", "process_unit_id": "pu"},
                {"visibility_code": "public", "corporate_entity_id": "other", "process_unit_id": "other"},
            )
        )
        return []

    monkeypatch.setattr(post_content_worker, "gather_chat_sources", gather)
    sources = asyncio.run(
        post_content_worker._operations_evidence_sources(
            _Pool(_Connection()),
            "post-1",
            {"corporate_entity_id": "corp", "process_unit_id": "pu"},
            SimpleNamespace(available=False),
        )
    )

    assert sources == ()
    assert decisions == [True, False, False, True]


def test_operations_sources_bind_milestones_to_source_owned_clocks(monkeypatch) -> None:
    """The source row, not model output, supplies each milestone instant."""
    observed_at = datetime(2026, 8, 1, 9, tzinfo=UTC)

    async def gather(*_args):
        return [SimpleNamespace(
            post_id="00000000-0000-0000-0000-000000000001",
            post_title="Synthetic claim",
            post_body="A claim was received.",
            evidence_facts=(),
        )]

    class SourceConnection(_Connection):
        async def fetch(self, query: str, *_args: object):
            assert "coalesce(event_occurred_at, created_at) as observed_at" in query
            assert isinstance(_args[0][0], UUID)
            return [{
                "post_id": "00000000-0000-0000-0000-000000000001",
                "event_occurred_at": observed_at,
                "observed_at": observed_at,
            }]

    monkeypatch.setattr(post_content_worker, "gather_chat_sources", gather)
    sources = asyncio.run(post_content_worker._operations_evidence_sources(
        _Pool(SourceConnection()),
        "00000000-0000-0000-0000-000000000001",
        {"corporate_entity_id": "corp", "process_unit_id": "pu"},
        SimpleNamespace(available=False),
    ))

    assert sources[0].observed_at == observed_at
    assert sources[0].time_axis_code == "event_occurred_at"
    assert sources[0].source_text == "A claim was received."


def test_operations_sources_retry_when_a_source_clock_disappears(monkeypatch) -> None:
    """A source deleted during assembly fails explicitly instead of inventing time."""

    async def gather(*_args):
        return [SimpleNamespace(
            post_id="00000000-0000-0000-0000-000000000001",
            post_title="Synthetic claim",
            post_body="A claim was received.",
            evidence_facts=(),
        )]

    class MissingClockConnection(_Connection):
        async def fetch(self, *_args: object):
            return []

    monkeypatch.setattr(post_content_worker, "gather_chat_sources", gather)
    with pytest.raises(RuntimeError, match="source clock unavailable"):
        asyncio.run(post_content_worker._operations_evidence_sources(
            _Pool(MissingClockConnection()),
            "00000000-0000-0000-0000-000000000001",
            {"corporate_entity_id": "corp", "process_unit_id": "pu"},
            SimpleNamespace(available=False),
        ))


def test_new_project_evidence_requeues_siblings_with_missing_facts(monkeypatch) -> None:
    """A newly analyzed project post wakes completed missing-fact analyses."""
    sibling_id = "00000000-0000-0000-0000-000000000002"

    class MissingFactConnection(_Connection):
        async def fetch(self, query: str, *_args: object):
            if "operations_case_missing_fact" in query:
                assert _args[1] == SUCCEEDED
                return [{"post_id": sibling_id, "post_body": "Synthetic sibling body"}]
            return []

    async def siblings(_conn, _post_id):
        return frozenset({sibling_id})

    queued: list[tuple[str, str, bool]] = []

    async def ensure(_conn, post_id, body, *, content_complete):
        queued.append((post_id, body, content_complete))
        return SimpleNamespace(should_publish=True)

    monkeypatch.setattr(post_content_worker, "find_project_sibling_post_ids", siblings)
    monkeypatch.setattr(post_content_worker, "ensure_post_content_job", ensure)

    count = asyncio.run(
        post_content_worker._requeue_project_missing_case_jobs(
            _Pool(MissingFactConnection()),
            "00000000-0000-0000-0000-000000000001",
        )
    )

    assert count == 1
    assert queued == [(sibling_id, "Synthetic sibling body", False)]


def test_missing_fact_requeue_stops_without_project_siblings(monkeypatch) -> None:
    """An unlinked post does not create speculative retry work."""

    async def no_siblings(_conn, _post_id):
        return frozenset()

    monkeypatch.setattr(
        post_content_worker,
        "find_project_sibling_post_ids",
        no_siblings,
    )

    assert (
        asyncio.run(
            post_content_worker._requeue_project_missing_case_jobs(
                _Pool(_Connection()),
                "00000000-0000-0000-0000-000000000001",
            )
        )
        == 0
    )


def test_terminal_failed_job_ignores_a_stale_duplicate_wakeup() -> None:
    connection = _Connection(_row(FAILED, POST_CONTENT_MAX_ATTEMPTS))

    claimed = asyncio.run(
        post_content_worker._claim_job(
            _Pool(connection),
            "00000000-0000-0000-0000-000000000001",
            "a" * 64,
            require_embedding=False,
        )
    )

    assert claimed is None
    assert connection.executed == []


def test_duplicate_wakeup_before_retry_delay_is_not_claimable() -> None:
    connection = _Connection(_row(QUEUED, 1), values=[False])

    claimed = asyncio.run(
        post_content_worker._claim_job(
            _Pool(connection),
            "00000000-0000-0000-0000-000000000001",
            "a" * 64,
            require_embedding=False,
        )
    )

    assert claimed is None
    assert connection.executed == []


def test_due_retry_is_claimed_and_attempt_is_incremented() -> None:
    connection = _Connection(_row(QUEUED, 1), values=[True])

    claimed = asyncio.run(
        post_content_worker._claim_job(
            _Pool(connection),
            "00000000-0000-0000-0000-000000000001",
            "a" * 64,
            require_embedding=False,
        )
    )

    assert claimed is not None
    assert any("attempt_count = attempt_count + 1" in query for query, _args in connection.executed)
    assert any(args[1] == RUNNING for query, args in connection.executed if len(args) > 1 and "set status_code" in query)


def test_successful_job_reclaims_when_configured_evidence_is_incomplete(monkeypatch) -> None:
    connection = _Connection(_row(SUCCEEDED, 0), values=[False])
    calls: list[str] = []

    async def incomplete(*_args, **_kwargs) -> bool:
        calls.append("checked")
        return False

    monkeypatch.setattr(post_content_worker, "post_content_is_complete", incomplete)
    claimed = asyncio.run(
        post_content_worker._claim_job(
            _Pool(connection),
            "00000000-0000-0000-0000-000000000001",
            "a" * 64,
            require_embedding=True,
            require_structure=True,
        )
    )

    assert claimed is not None
    assert calls == ["checked"]


def test_successful_job_reclaims_when_product_analysis_is_missing(monkeypatch) -> None:
    """Historical content is reclaimed until its exact product analysis exists."""
    row = _row(SUCCEEDED, 0)
    row["product_analysis_source_body_sha256"] = None
    connection = _Connection(row, values=[True])

    async def complete(*_args, **_kwargs) -> bool:
        return True

    monkeypatch.setattr(post_content_worker, "post_content_is_complete", complete)
    claimed = asyncio.run(
        post_content_worker._claim_job(
            _Pool(connection),
            "00000000-0000-0000-0000-000000000001",
            "a" * 64,
            require_embedding=True,
            require_structure=True,
        )
    )

    assert claimed is row
    assert any(
        "attempt_count = attempt_count + 1" in query
        for query, _args in connection.executed
    )


def test_successful_job_reclaims_when_voice_receipt_is_missing(monkeypatch) -> None:
    """A successful job is incomplete until the exact Voice receipt exists."""
    row = _row(SUCCEEDED, 0)
    row["product_analysis_source_body_sha256"] = "a" * 64
    row["voice_analysis_source_body_sha256"] = None
    connection = _Connection(row, values=[True, True])

    async def complete(*_args, **_kwargs) -> bool:
        return True

    monkeypatch.setattr(post_content_worker, "post_content_is_complete", complete)
    claimed = asyncio.run(
        post_content_worker._claim_job(
            _Pool(connection),
            "00000000-0000-0000-0000-000000000001",
            "a" * 64,
            require_embedding=True,
            require_structure=True,
        )
    )

    assert claimed is row


def test_independent_receipts_persist_before_operations_failure(monkeypatch) -> None:
    """An operations outage cannot suppress independent Voice or product producers."""
    persisted: list[str] = []
    failed_stages: list[str | None] = []

    async def claim(*_args, **_kwargs):
        return _row(RUNNING, 1)

    async def persist_voice(*_args, **_kwargs):
        persisted.append("voice")

    async def persist_product(*_args, **_kwargs):
        persisted.append("product")

    async def fail_operations(*_args, **_kwargs):
        raise RuntimeError("synthetic operations failure")

    async def finish_failed(_pool, _post_id, **kwargs):
        failed_stages.append(kwargs.get("channel_stage_code"))

    monkeypatch.setattr(post_content_worker, "_claim_job", claim)
    monkeypatch.setattr(
        post_content_worker,
        "load_settings",
        lambda: SimpleNamespace(orchestrator_base_url="gateway", orchestrator_api_key="key"),
    )
    monkeypatch.setattr(
        post_content_worker, "_persist_voice_classification_if_needed", persist_voice
    )
    monkeypatch.setattr(
        post_content_worker,
        "_operations_evidence_sources",
        lambda *_args, **_kwargs: asyncio.sleep(0, result=()),
    )
    monkeypatch.setattr(
        post_content_worker,
        "_persist_operations_case_analysis_if_needed",
        fail_operations,
    )
    monkeypatch.setattr(
        post_content_worker, "_persist_product_analysis_if_needed", persist_product
    )
    monkeypatch.setattr(
        post_content_worker,
        "extract_occupational_construct_assertions",
        lambda *_args, **_kwargs: asyncio.sleep(0, result=()),
    )
    monkeypatch.setattr(
        post_content_worker,
        "persist_occupational_construct_assertions",
        lambda *_args, **_kwargs: asyncio.sleep(0),
    )
    monkeypatch.setattr(post_content_worker, "normalize_post_body", lambda *_args: object())
    monkeypatch.setattr(
        post_content_worker, "persist_post_content", lambda *_args, **_kwargs: asyncio.sleep(0)
    )
    monkeypatch.setattr(post_content_worker, "_finish_failed_job", finish_failed)
    monkeypatch.setattr(
        post_content_worker, "record_server_failure", lambda *_args, **_kwargs: None
    )
    client = SimpleNamespace(available=True, resolved_model="synthetic-model")

    asyncio.run(
        post_content_worker.process_post_content_job(
            _Pool(_Connection()),
            post_id="00000000-0000-0000-0000-000000000001",
            source_body_digest="a" * 64,
            vision_factory=lambda: client,
            embedding_factory=lambda: client,
            structure_factory=lambda: client,
        )
    )

    assert persisted == ["voice", "product"]
    assert failed_stages == ["operations_case"]


def test_voice_failure_does_not_starve_independent_operations(monkeypatch) -> None:
    """A failed Voice channel retries after other independent evidence persists."""
    persisted: list[str] = []
    failed_stages: list[str | None] = []

    async def claim(*_args, **_kwargs):
        return _row(RUNNING, 1)

    async def fail_voice(*_args, **_kwargs):
        raise ValueError("synthetic invalid Voice response")

    async def persist_operations(*_args, **_kwargs):
        persisted.append("operations")

    async def finish_failed(_pool, _post_id, **kwargs):
        failed_stages.append(kwargs.get("channel_stage_code"))

    monkeypatch.setattr(post_content_worker, "_claim_job", claim)
    monkeypatch.setattr(
        post_content_worker,
        "load_settings",
        lambda: SimpleNamespace(orchestrator_base_url="gateway", orchestrator_api_key="key"),
    )
    monkeypatch.setattr(
        post_content_worker, "_persist_voice_classification_if_needed", fail_voice
    )
    monkeypatch.setattr(
        post_content_worker,
        "_operations_evidence_sources",
        lambda *_args, **_kwargs: asyncio.sleep(0, result=()),
    )
    monkeypatch.setattr(
        post_content_worker,
        "_persist_operations_case_analysis_if_needed",
        persist_operations,
    )
    monkeypatch.setattr(
        post_content_worker,
        "extract_occupational_construct_assertions",
        lambda *_args, **_kwargs: asyncio.sleep(0, result=()),
    )
    monkeypatch.setattr(
        post_content_worker,
        "persist_occupational_construct_assertions",
        lambda *_args, **_kwargs: asyncio.sleep(0),
    )
    monkeypatch.setattr(post_content_worker, "normalize_post_body", lambda *_args: object())
    monkeypatch.setattr(
        post_content_worker, "persist_post_content", lambda *_args, **_kwargs: asyncio.sleep(0)
    )
    monkeypatch.setattr(post_content_worker, "_finish_failed_job", finish_failed)
    monkeypatch.setattr(
        post_content_worker, "record_server_failure", lambda *_args, **_kwargs: None
    )
    client = SimpleNamespace(available=True, resolved_model="synthetic-model")

    asyncio.run(
        post_content_worker.process_post_content_job(
            _Pool(_Connection()),
            post_id="00000000-0000-0000-0000-000000000001",
            source_body_digest="a" * 64,
            vision_factory=lambda: client,
            embedding_factory=lambda: client,
            structure_factory=lambda: client,
        )
    )

    assert persisted == ["operations"]
    assert failed_stages == ["voice_classification"]


def test_voice_admission_defer_waits_for_independent_operations(monkeypatch) -> None:
    """Voice admission delay is preserved after independent evidence persists."""
    persisted: list[str] = []
    deferred: list[tuple[int, int]] = []

    async def claim(*_args, **_kwargs):
        return _row(RUNNING, 1)

    async def defer_voice(*_args, **_kwargs):
        raise HttpAdmissionDeferred(30)

    async def persist_operations(*_args, **_kwargs):
        persisted.append("operations")

    async def defer(*_args, expected_attempt_count: int, retry_after_seconds: int, **_kwargs):
        deferred.append((expected_attempt_count, retry_after_seconds))
        return True

    monkeypatch.setattr(post_content_worker, "_claim_job", claim)
    monkeypatch.setattr(
        post_content_worker,
        "load_settings",
        lambda: SimpleNamespace(orchestrator_base_url="gateway", orchestrator_api_key="key"),
    )
    monkeypatch.setattr(
        post_content_worker, "_persist_voice_classification_if_needed", defer_voice
    )
    monkeypatch.setattr(
        post_content_worker,
        "_operations_evidence_sources",
        lambda *_args, **_kwargs: asyncio.sleep(0, result=()),
    )
    monkeypatch.setattr(
        post_content_worker,
        "_persist_operations_case_analysis_if_needed",
        persist_operations,
    )
    monkeypatch.setattr(
        post_content_worker,
        "extract_occupational_construct_assertions",
        lambda *_args, **_kwargs: asyncio.sleep(0, result=()),
    )
    monkeypatch.setattr(
        post_content_worker,
        "persist_occupational_construct_assertions",
        lambda *_args, **_kwargs: asyncio.sleep(0),
    )
    monkeypatch.setattr(post_content_worker, "normalize_post_body", lambda *_args: object())
    monkeypatch.setattr(
        post_content_worker, "persist_post_content", lambda *_args, **_kwargs: asyncio.sleep(0)
    )
    monkeypatch.setattr(post_content_worker, "defer_post_content_job", defer)
    client = SimpleNamespace(available=True, resolved_model="synthetic-model")

    asyncio.run(
        post_content_worker.process_post_content_job(
            _Pool(_Connection()),
            post_id="00000000-0000-0000-0000-000000000001",
            source_body_digest="a" * 64,
            vision_factory=lambda: client,
            embedding_factory=lambda: client,
            structure_factory=lambda: client,
        )
    )

    assert persisted == ["operations"]
    assert deferred == [(2, 30)]


def test_admission_defer_does_not_hide_independent_hard_failure(monkeypatch) -> None:
    """A hard stage failure consumes its retry even when another stage defers."""
    failed_stages: list[str | None] = []
    deferred: list[int] = []

    async def claim(*_args, **_kwargs):
        return _row(RUNNING, 1)

    async def fail_voice(*_args, **_kwargs):
        raise ValueError("synthetic invalid Voice response")

    async def defer_operations(*_args, **_kwargs):
        raise HttpAdmissionDeferred(30)

    async def finish_failed(_pool, _post_id, **kwargs):
        failed_stages.append(kwargs.get("channel_stage_code"))

    async def defer(*_args, **_kwargs):
        deferred.append(1)
        return True

    monkeypatch.setattr(post_content_worker, "_claim_job", claim)
    monkeypatch.setattr(
        post_content_worker,
        "load_settings",
        lambda: SimpleNamespace(orchestrator_base_url="gateway", orchestrator_api_key="key"),
    )
    monkeypatch.setattr(
        post_content_worker, "_persist_voice_classification_if_needed", fail_voice
    )
    monkeypatch.setattr(
        post_content_worker,
        "_operations_evidence_sources",
        lambda *_args, **_kwargs: asyncio.sleep(0, result=()),
    )
    monkeypatch.setattr(
        post_content_worker,
        "_persist_operations_case_analysis_if_needed",
        defer_operations,
    )
    monkeypatch.setattr(
        post_content_worker,
        "extract_occupational_construct_assertions",
        lambda *_args, **_kwargs: asyncio.sleep(0, result=()),
    )
    monkeypatch.setattr(
        post_content_worker,
        "persist_occupational_construct_assertions",
        lambda *_args, **_kwargs: asyncio.sleep(0),
    )
    monkeypatch.setattr(post_content_worker, "normalize_post_body", lambda *_args: object())
    monkeypatch.setattr(
        post_content_worker, "persist_post_content", lambda *_args, **_kwargs: asyncio.sleep(0)
    )
    monkeypatch.setattr(post_content_worker, "_finish_failed_job", finish_failed)
    monkeypatch.setattr(post_content_worker, "defer_post_content_job", defer)
    monkeypatch.setattr(
        post_content_worker, "record_server_failure", lambda *_args, **_kwargs: None
    )
    client = SimpleNamespace(available=True, resolved_model="synthetic-model")

    asyncio.run(
        post_content_worker.process_post_content_job(
            _Pool(_Connection()),
            post_id="00000000-0000-0000-0000-000000000001",
            source_body_digest="a" * 64,
            vision_factory=lambda: client,
            embedding_factory=lambda: client,
            structure_factory=lambda: client,
        )
    )

    assert failed_stages == ["voice_classification"]
    assert deferred == []


def test_incomplete_provider_output_is_requeued_with_a_failure_code(monkeypatch) -> None:
    connection = _Connection(values=[False, 2])
    pool = _Pool(connection)

    async def claim(*_args, **_kwargs):
        return _row(RUNNING, 1)

    async def persist(*_args, **_kwargs):
        return 1

    async def incomplete(*_args, **_kwargs):
        return False

    monkeypatch.setattr(post_content_worker, "_claim_job", claim)
    monkeypatch.setattr(post_content_worker, "persist_post_content", persist)
    monkeypatch.setattr(post_content_worker, "post_content_is_complete", incomplete)
    monkeypatch.setattr(
        post_content_worker,
        "load_settings",
        lambda: SimpleNamespace(
            orchestrator_base_url="gateway",
            orchestrator_api_key="key",
        ),
    )
    monkeypatch.setattr(
        post_content_worker,
        "normalize_post_body",
        lambda *_args: SimpleNamespace(text="synthetic source body"),
    )
    async def evidence_sources(*_args, **_kwargs):
        return (OperationsEvidenceSource("post-1", "Synthetic", "A synthetic post body with a retrieval unit."),)

    monkeypatch.setattr(post_content_worker, "_operations_evidence_sources", evidence_sources)
    analyzed_bodies: list[str] = []
    monkeypatch.setattr(
        post_content_worker,
        "ContextualOrchestratorOperationsCaseAnalysisClient",
        lambda *_args: SimpleNamespace(
            analyze=lambda sources, _context: analyzed_bodies.append(sources[0].text) or ()
        ),
    )
    monkeypatch.setattr(post_content_worker, "persist_operations_cases", persist)
    monkeypatch.setattr(
        post_content_worker,
        "extract_occupational_construct_assertions",
        lambda *_args, **_kwargs: asyncio.sleep(0, result=()),
    )
    monkeypatch.setattr(
        post_content_worker, "persist_occupational_construct_assertions", persist
    )
    client = SimpleNamespace(available=True)

    asyncio.run(
        post_content_worker.process_post_content_job(
            pool,
            post_id="00000000-0000-0000-0000-000000000001",
            source_body_digest="a" * 64,
            vision_factory=lambda: client,
            embedding_factory=lambda: client,
            structure_factory=lambda: client,
        )
    )

    updates = [args for query, args in connection.executed if "set status_code" in query]
    incomplete_update = next(
        args
        for args in updates
        if args[1] == QUEUED and args[6] == "post_content_ingestion_incomplete"
    )
    assert incomplete_update[9] == "content_persistence"
    assert incomplete_update[13]
    assert analyzed_bodies == ["A synthetic post body with a retrieval unit."]


def test_existing_case_analysis_skips_duplicate_orchestrator_call(monkeypatch) -> None:
    """A retry preserves the same exact input without another provider call."""
    connection = _Connection(values=[True])
    called: list[str] = []

    async def evidence_sources(*_args, **_kwargs):
        return (OperationsEvidenceSource("post-1", "Synthetic", "Evidence"),)

    monkeypatch.setattr(
        post_content_worker, "_operations_evidence_sources", evidence_sources
    )
    monkeypatch.setattr(
        post_content_worker,
        "ContextualOrchestratorOperationsCaseAnalysisClient",
        lambda *_args: called.append("client") or SimpleNamespace(),
    )

    asyncio.run(
        post_content_worker._persist_operations_case_analysis_if_needed(
            _Pool(connection),
            "00000000-0000-0000-0000-000000000001",
            "a" * 64,
            "Synthetic source body",
            _row(RUNNING, 1),
            SimpleNamespace(available=True),
            "synthetic-session",
            "gateway",
            "key",
        )
    )

    assert called == []


def test_product_analysis_persists_one_exact_authorized_window(monkeypatch) -> None:
    """Product extraction uses only the exact authorized focal source."""
    connection = _Connection(values=[False])
    events: list[object] = []
    submitted_sources: list[object] = []

    async def resolve(_conn, mentions):
        events.append(mentions)
        return (SimpleNamespace(
            mention=mentions[0], resolution_status_code="missing", product_catalog_id=None
        ),)

    async def persist(*args, **kwargs):
        events.append((args, kwargs))

    monkeypatch.setattr(
        post_content_worker,
        "ContextualOrchestratorProductExtractionClient",
        lambda *_args: SimpleNamespace(
            extract=lambda sources, targets, session_id: SimpleNamespace(
                extraction=SimpleNamespace(
                    mentions=(
                        ProductMention(
                            "Synthetic Product Q",
                            "Synthetic Product Q",
                            sources[0].post_id,
                            sources[0].input_sha256,
                        ),
                    ),
                    relations=(),
                ),
            ) if session_id == "session-a" and not submitted_sources.extend(sources) else None,
        ),
    )
    monkeypatch.setattr(post_content_worker, "resolve_product_mentions", resolve)
    monkeypatch.setattr(post_content_worker, "persist_product_mentions", persist)

    asyncio.run(
        _PRODUCT_ANALYSIS(
            _Pool(connection),
            "post-1",
            "a" * 64,
            "Synthetic Product Q",
            "session-a",
            "gateway",
            "key",
            None,
        )
    )
    assert len(events) == 2
    persist_args, persist_kwargs = events[1]
    assert len(persist_args[2]) == 64
    assert persist_kwargs == {"expected_operations_input_sha256": None}
    assert submitted_sources[0].text == "Synthetic Product Q"
    assert [source.post_id for source in submitted_sources] == ["post-1"]
    operation_query, operation_args = connection.fetched[0]
    assert "analysis.source_body_sha256 = $2" in operation_query
    assert "analysis.analysis_input_sha256 = $3" in operation_query
    assert operation_args == ("post-1", "a" * 64, None)
    project_query, project_args = connection.fetched[1]
    assert "strpos(coalesce(source.post_body, ''), project.evidence_text) > 0" in project_query
    assert project_args == ("post-1", "a" * 64)


def test_product_analysis_skips_same_digest(monkeypatch) -> None:
    """A durable retry does not repeat product extraction for the same input."""
    connection = _Connection(values=[True])

    monkeypatch.setattr(
        post_content_worker,
        "ContextualOrchestratorProductExtractionClient",
        lambda *_args: (_ for _ in ()).throw(AssertionError("must not call provider")),
    )
    asyncio.run(
        _PRODUCT_ANALYSIS(
            _Pool(connection), "post-1", "a" * 64,
            "Synthetic Product Q", "session-a", "gateway", "key", None,
        )
    )


def test_changed_evidence_window_reanalyzes_unchanged_body(monkeypatch) -> None:
    """A newly available sibling invalidates reuse without changing focal text."""
    connection = _Connection(values=[False])
    analyzed: list[tuple[OperationsEvidenceSource, ...]] = []
    persisted: list[str] = []

    async def evidence_sources(*_args, **_kwargs):
        return (
            OperationsEvidenceSource("post-1", "Focal", "Focal evidence"),
            OperationsEvidenceSource("post-2", "Sibling", "New sibling evidence"),
        )

    async def persist(*_args, **kwargs):
        persisted.append(str(kwargs["analysis_input_sha256"]))

    monkeypatch.setattr(
        post_content_worker, "_operations_evidence_sources", evidence_sources
    )
    monkeypatch.setattr(
        post_content_worker,
        "ContextualOrchestratorOperationsCaseAnalysisClient",
        lambda *_args: SimpleNamespace(
            analyze=lambda sources, _context: analyzed.append(sources) or ()
        ),
    )
    monkeypatch.setattr(post_content_worker, "persist_operations_cases", persist)

    asyncio.run(
        post_content_worker._persist_operations_case_analysis_if_needed(
            _Pool(connection),
            "00000000-0000-0000-0000-000000000001",
            "a" * 64,
            "Synthetic source body",
            _row(RUNNING, 1),
            SimpleNamespace(available=True),
            "synthetic-session",
            "gateway",
            "key",
        )
    )

    assert [source.post_id for source in analyzed[0]] == ["post-1", "post-2"]
    assert len(persisted[0]) == 64


def test_sibling_requeue_failure_preserves_completed_primary_job(monkeypatch) -> None:
    """Ancillary retry discovery cannot fail already-persisted post evidence."""
    outcomes: list[str] = []

    async def claim(*_args, **_kwargs):
        return _row(RUNNING, 1)

    async def complete(*_args, **_kwargs):
        return True

    async def fail_requeue(*_args, **_kwargs):
        raise OSError("synthetic sibling lookup outage")

    async def finish(_pool, _post_id, status, **_kwargs):
        outcomes.append(status)

    monkeypatch.setattr(post_content_worker, "_claim_job", claim)
    monkeypatch.setattr(
        post_content_worker,
        "load_settings",
        lambda: SimpleNamespace(orchestrator_base_url="gateway", orchestrator_api_key="key"),
    )
    monkeypatch.setattr(
        post_content_worker,
        "_persist_operations_case_analysis_if_needed",
        lambda *_args, **_kwargs: asyncio.sleep(0),
    )
    monkeypatch.setattr(
        post_content_worker,
        "extract_occupational_construct_assertions",
        lambda *_args, **_kwargs: asyncio.sleep(0, result=()),
    )
    monkeypatch.setattr(
        post_content_worker,
        "persist_occupational_construct_assertions",
        lambda *_args, **_kwargs: asyncio.sleep(0),
    )
    monkeypatch.setattr(
        post_content_worker,
        "_operations_evidence_sources",
        lambda *_args, **_kwargs: asyncio.sleep(
            0,
            result=(OperationsEvidenceSource("post-1", "Synthetic", "Evidence"),),
        ),
    )
    monkeypatch.setattr(post_content_worker, "normalize_post_body", lambda *_args: object())
    monkeypatch.setattr(
        post_content_worker,
        "persist_post_content",
        lambda *_args, **_kwargs: asyncio.sleep(0),
    )
    monkeypatch.setattr(post_content_worker, "post_content_is_complete", complete)
    monkeypatch.setattr(post_content_worker, "_requeue_project_missing_case_jobs", fail_requeue)
    monkeypatch.setattr(post_content_worker, "_finish_job", finish)
    monkeypatch.setattr(
        post_content_worker, "record_server_failure", lambda *_args, **_kwargs: None
    )
    client = SimpleNamespace(available=True, resolved_model="synthetic-model")

    asyncio.run(
        post_content_worker.process_post_content_job(
            _Pool(_Connection()),
            post_id="00000000-0000-0000-0000-000000000001",
            source_body_digest="a" * 64,
            vision_factory=lambda: client,
            embedding_factory=lambda: client,
            structure_factory=lambda: client,
        )
    )

    assert outcomes == [SUCCEEDED]


def test_invalid_product_output_keeps_the_job_retryable(monkeypatch) -> None:
    """A missing product signal cannot be mislabeled as a succeeded job."""
    outcomes: list[str] = []
    persisted: list[str] = []
    failures: list[tuple[str, str]] = []
    failed_stages: list[str | None] = []
    channel_order: list[str] = []

    async def claim(*_args, **_kwargs):
        return _row(RUNNING, 1)

    async def fail_product(*_args, **_kwargs):
        channel_order.append("product")
        raise RuntimeError("synthetic malformed product response")

    async def persist_cases(*_args, **_kwargs):
        channel_order.append("cases")
        persisted.append("cases")

    async def persist_content(*_args, **_kwargs):
        persisted.append("content")

    async def finish(_pool, _post_id, status, **_kwargs):
        outcomes.append(status)

    async def finish_failed(_pool, _post_id, **kwargs):
        failed_stages.append(kwargs.get("channel_stage_code"))

    monkeypatch.setattr(post_content_worker, "_claim_job", claim)
    monkeypatch.setattr(
        post_content_worker,
        "load_settings",
        lambda: SimpleNamespace(
            orchestrator_base_url="gateway", orchestrator_api_key="key"
        ),
    )
    monkeypatch.setattr(
        post_content_worker,
        "_operations_evidence_sources",
        lambda *_args, **_kwargs: asyncio.sleep(
            0,
            result=(OperationsEvidenceSource("post-1", "Synthetic", "Evidence"),),
        ),
    )
    monkeypatch.setattr(
        post_content_worker, "_persist_product_analysis_if_needed", fail_product
    )
    monkeypatch.setattr(
        post_content_worker,
        "_persist_operations_case_analysis_if_needed",
        persist_cases,
    )
    monkeypatch.setattr(
        post_content_worker,
        "extract_occupational_construct_assertions",
        lambda *_args, **_kwargs: asyncio.sleep(0, result=()),
    )
    monkeypatch.setattr(
        post_content_worker,
        "persist_occupational_construct_assertions",
        lambda *_args, **_kwargs: asyncio.sleep(0),
    )
    monkeypatch.setattr(post_content_worker, "normalize_post_body", lambda *_args: object())
    monkeypatch.setattr(post_content_worker, "persist_post_content", persist_content)
    monkeypatch.setattr(
        post_content_worker,
        "post_content_is_complete",
        lambda *_args, **_kwargs: asyncio.sleep(0, result=True),
    )
    monkeypatch.setattr(
        post_content_worker, "_requeue_project_missing_case_jobs", lambda *_args: asyncio.sleep(0)
    )
    monkeypatch.setattr(post_content_worker, "_finish_job", finish)
    monkeypatch.setattr(post_content_worker, "_finish_failed_job", finish_failed)
    monkeypatch.setattr(
        post_content_worker,
        "record_server_failure",
        lambda operation, _exc, *, outcome: failures.append((operation, outcome)),
    )
    client = SimpleNamespace(available=True, resolved_model="synthetic-model")

    asyncio.run(
        post_content_worker.process_post_content_job(
            _Pool(_Connection()),
            post_id="00000000-0000-0000-0000-000000000001",
            source_body_digest="a" * 64,
            vision_factory=lambda: client,
            embedding_factory=lambda: client,
            structure_factory=lambda: client,
        )
    )

    assert persisted == ["cases", "content"]
    assert channel_order == ["cases", "product"]
    assert outcomes == []
    assert failed_stages == ["product_analysis"]
    assert failures == [
        ("product_semantic_ingestion", "provider_unavailable"),
        ("post_content_ingestion", "internal_error"),
    ]


def test_occupational_construct_failure_keeps_its_own_stage(monkeypatch) -> None:
    """Construct extraction failures are not mislabeled as product failures."""
    failed_stages: list[str | None] = []

    async def claim(*_args, **_kwargs):
        return _row(RUNNING, 1)

    async def fail_construct(*_args, **_kwargs):
        raise ValueError("synthetic construct response")

    async def finish_failed(_pool, _post_id, **kwargs):
        failed_stages.append(kwargs.get("channel_stage_code"))

    monkeypatch.setattr(post_content_worker, "_claim_job", claim)
    monkeypatch.setattr(
        post_content_worker,
        "load_settings",
        lambda: SimpleNamespace(
            orchestrator_base_url="gateway", orchestrator_api_key="key"
        ),
    )
    monkeypatch.setattr(
        post_content_worker,
        "_operations_evidence_sources",
        lambda *_args, **_kwargs: asyncio.sleep(
            0,
            result=(OperationsEvidenceSource("post-1", "Synthetic", "Evidence"),),
        ),
    )
    monkeypatch.setattr(
        post_content_worker,
        "_persist_operations_case_analysis_if_needed",
        lambda *_args, **_kwargs: asyncio.sleep(0),
    )
    monkeypatch.setattr(
        post_content_worker,
        "_persist_product_analysis_if_needed",
        lambda *_args, **_kwargs: asyncio.sleep(0),
    )
    monkeypatch.setattr(
        post_content_worker, "extract_occupational_construct_assertions", fail_construct
    )
    monkeypatch.setattr(post_content_worker, "_finish_failed_job", finish_failed)
    monkeypatch.setattr(
        post_content_worker,
        "record_server_failure",
        lambda *_args, **_kwargs: None,
    )
    client = SimpleNamespace(available=True, resolved_model="synthetic-model")

    asyncio.run(
        post_content_worker.process_post_content_job(
            _Pool(_Connection()),
            post_id="00000000-0000-0000-0000-000000000001",
            source_body_digest="a" * 64,
            vision_factory=lambda: client,
            embedding_factory=lambda: client,
            structure_factory=lambda: client,
        )
    )

    assert failed_stages == ["occupational_construct"]


def test_case_analysis_persists_before_content_provider_failure(monkeypatch) -> None:
    """Independent case evidence survives a later structure or embedding outage."""
    connection = _Connection(values=[False, 2])
    pool = _Pool(connection)
    persisted: list[str] = []

    async def claim(*_args, **_kwargs):
        return _row(RUNNING, 1)

    async def fail_content(*_args, **_kwargs):
        raise TimeoutError("synthetic provider timeout")

    async def evidence_sources(*_args, **_kwargs):
        return (
            OperationsEvidenceSource(
                "post-1", "Synthetic", "A synthetic source body."
            ),
        )

    async def persist_cases(_conn, _post_id, *_args, **_kwargs):
        persisted.append("cases")

    monkeypatch.setattr(post_content_worker, "_claim_job", claim)
    monkeypatch.setattr(post_content_worker, "persist_post_content", fail_content)
    monkeypatch.setattr(
        post_content_worker,
        "load_settings",
        lambda: SimpleNamespace(
            orchestrator_base_url="gateway", orchestrator_api_key="key"
        ),
    )
    monkeypatch.setattr(
        post_content_worker, "_operations_evidence_sources", evidence_sources
    )
    monkeypatch.setattr(
        post_content_worker,
        "ContextualOrchestratorOperationsCaseAnalysisClient",
        lambda *_args: SimpleNamespace(analyze=lambda *_args: ()),
    )
    monkeypatch.setattr(post_content_worker, "persist_operations_cases", persist_cases)
    monkeypatch.setattr(
        post_content_worker, "normalize_post_body", lambda *_args: object()
    )
    client = SimpleNamespace(available=True)

    asyncio.run(
        post_content_worker.process_post_content_job(
            pool,
            post_id="00000000-0000-0000-0000-000000000001",
            source_body_digest="a" * 64,
            vision_factory=lambda: client,
            embedding_factory=lambda: client,
            structure_factory=lambda: client,
        )
    )

    assert persisted == ["cases"]
    updates = [
        args for query, args in connection.executed if "set status_code" in query
    ]
    assert any(args[1] == QUEUED for args in updates)


def test_missing_source_body_is_not_reported_as_a_provider_failure(monkeypatch, caplog) -> None:
    connection = _Connection(values=[2])
    pool = _Pool(connection)

    async def claim(*_args, **_kwargs):
        return _row(RUNNING, 1) | {"post_body": "   "}

    monkeypatch.setattr(post_content_worker, "_claim_job", claim)
    monkeypatch.setattr(
        post_content_worker,
        "load_settings",
        lambda: SimpleNamespace(
            embedding_model="embedding-model",
            orchestrator_base_url="",
            orchestrator_api_key="",
        ),
    )
    client = SimpleNamespace(available=True)

    with caplog.at_level("WARNING", logger=post_content_worker._logger.name):
        asyncio.run(
            post_content_worker.process_post_content_job(
                pool,
                post_id="00000000-0000-0000-0000-000000000001",
                source_body_digest="a" * 64,
                vision_factory=lambda: client,
                embedding_factory=lambda: client,
                structure_factory=lambda: client,
            )
        )

    updates = [args for query, args in connection.executed if "set status_code" in query]
    assert any(
        args[1] == FAILED
        and args[6] == "post_content_source_body_missing"
        and args[7] == "source post has no body"
        for args in updates
    )
    assert any(
        "source post has no body" in record.message for record in caplog.records
    ), "empty-body skip must still emit a diagnostic log line"


def test_transient_provider_error_is_requeued_before_attempt_limit(monkeypatch, caplog) -> None:
    caplog.set_level("WARNING", logger="lineageweave.observability")
    connection = _Connection(values=[2])
    pool = _Pool(connection)

    async def claim(*_args, **_kwargs):
        return _row(RUNNING, 1)

    async def persist(*_args, **_kwargs):
        raise TimeoutError("provider timeout")

    monkeypatch.setattr(post_content_worker, "_claim_job", claim)
    monkeypatch.setattr(post_content_worker, "persist_post_content", persist)
    monkeypatch.setattr(
        post_content_worker,
        "load_settings",
        lambda: SimpleNamespace(
            orchestrator_base_url="",
            orchestrator_api_key="",
        ),
    )
    monkeypatch.setattr(post_content_worker, "normalize_post_body", lambda *_args: object())
    client = SimpleNamespace(available=True)

    asyncio.run(
        post_content_worker.process_post_content_job(
            pool,
            post_id="00000000-0000-0000-0000-000000000001",
            source_body_digest="a" * 64,
            vision_factory=lambda: client,
            embedding_factory=lambda: client,
            structure_factory=lambda: client,
        )
    )

    updates = [args for query, args in connection.executed if "set status_code" in query]
    assert any(
        args[1] == QUEUED
        and args[6] == "post_content_ingestion_failed"
        and args[7] == post_content_worker._UNEXPECTED_FAILURE_DETAIL
        for args in updates
    )
    assert all("provider timeout" not in str(args) for args in updates)
    assert "provider timeout" not in caplog.text
    record = next(
        item for item in caplog.records if item.msg == "lineageweave.server_failure"
    )
    assert record.failure_outcome == "provider_unavailable"


def test_worker_persists_bounded_failure_provenance(monkeypatch) -> None:
    """A failed channel records typed diagnostics without remote content."""

    connection = _Connection(values=[1])
    pool = _Pool(connection)

    async def claim(*_args, **_kwargs):
        return _row(RUNNING, 0)

    async def persist(*_args, **_kwargs):
        raise HttpClientError(
            "sanitized",
            http_status=504,
            remote_error_code="request_deadline_exceeded",
            retryable=True,
        )

    monkeypatch.setattr(post_content_worker, "_claim_job", claim)
    monkeypatch.setattr(post_content_worker, "persist_post_content", persist)
    monkeypatch.setattr(post_content_worker, "normalize_post_body", lambda *_args: object())
    monkeypatch.setattr(
        post_content_worker,
        "load_settings",
        lambda: SimpleNamespace(orchestrator_base_url="", orchestrator_api_key=""),
    )
    client = SimpleNamespace(available=True)
    asyncio.run(
        post_content_worker.process_post_content_job(
            pool,
            post_id="00000000-0000-0000-0000-000000000001",
            source_body_digest="a" * 64,
            vision_factory=lambda: client,
            embedding_factory=lambda: client,
            structure_factory=lambda: client,
        )
    )
    update = next(args for query, args in connection.executed if "set status_code" in query)
    assert update[9:13] == (
        "content_persistence",
        504,
        "request_deadline_exceeded",
        True,
    )
    assert isinstance(update[13], str) and len(update[13]) <= 128
    assert update[14] == "http_client_error"
    assert update[15:17] == (None, None)
    assert "sanitized" not in str(update)


def test_no_viable_agent_defers_without_consuming_failure_budget(monkeypatch) -> None:
    """Provider admission refusal uses the exact durable deferral transition."""
    connection = _Connection()
    pool = _Pool(connection)
    deferred: list[tuple[int, int]] = []

    async def claim(*_args, **_kwargs):
        return _row(RUNNING, 0)

    async def no_viable(*_args, **_kwargs):
        raise HttpAdmissionDeferred(30)

    async def evidence_sources(*_args, **_kwargs):
        return ()

    async def defer(*_args, expected_attempt_count: int, retry_after_seconds: int, **_kwargs):
        deferred.append((expected_attempt_count, retry_after_seconds))
        return True

    monkeypatch.setattr(post_content_worker, "_claim_job", claim)
    monkeypatch.setattr(
        post_content_worker,
        "_persist_operations_case_analysis_if_needed",
        no_viable,
    )
    monkeypatch.setattr(
        post_content_worker,
        "_operations_evidence_sources",
        evidence_sources,
    )
    monkeypatch.setattr(
        post_content_worker,
        "extract_occupational_construct_assertions",
        lambda *_args, **_kwargs: asyncio.sleep(0, result=()),
    )
    monkeypatch.setattr(
        post_content_worker,
        "persist_occupational_construct_assertions",
        lambda *_args, **_kwargs: asyncio.sleep(0),
    )
    monkeypatch.setattr(post_content_worker, "normalize_post_body", lambda *_args: object())
    monkeypatch.setattr(
        post_content_worker, "persist_post_content", lambda *_args, **_kwargs: asyncio.sleep(0)
    )
    monkeypatch.setattr(post_content_worker, "defer_post_content_job", defer)
    monkeypatch.setattr(
        post_content_worker,
        "load_settings",
        lambda: SimpleNamespace(
            orchestrator_base_url="http://orchestrator",
            orchestrator_api_key="synthetic-token",
        ),
    )
    client = SimpleNamespace(available=True)

    asyncio.run(
        post_content_worker.process_post_content_job(
            pool,
            post_id="00000000-0000-0000-0000-000000000001",
            source_body_digest="a" * 64,
            vision_factory=lambda: client,
            embedding_factory=lambda: client,
            structure_factory=lambda: client,
        )
    )

    assert deferred == [(1, 30)]
    assert not any("post_content_ingestion_failed" in str(args) for _, args in connection.executed)


def test_unexpected_worker_error_is_classified_as_internal(monkeypatch, caplog) -> None:
    """Unexpected worker defects stay internal while their value remains private."""
    caplog.set_level("ERROR", logger="lineageweave.observability")
    connection = _Connection(values=[2])
    pool = _Pool(connection)

    async def claim(*_args, **_kwargs):
        return _row(RUNNING, 1)

    async def persist(*_args, **_kwargs):
        raise TypeError("internal worker detail")

    monkeypatch.setattr(post_content_worker, "_claim_job", claim)
    monkeypatch.setattr(post_content_worker, "persist_post_content", persist)
    monkeypatch.setattr(
        post_content_worker,
        "load_settings",
        lambda: SimpleNamespace(
            embedding_model="embedding-model",
            orchestrator_base_url="",
            orchestrator_api_key="",
        ),
    )
    monkeypatch.setattr(post_content_worker, "normalize_post_body", lambda *_args: object())
    client = SimpleNamespace(available=True)

    asyncio.run(
        post_content_worker.process_post_content_job(
            pool,
            post_id="00000000-0000-0000-0000-000000000001",
            source_body_digest="a" * 64,
            vision_factory=lambda: client,
            embedding_factory=lambda: client,
            structure_factory=lambda: client,
        )
    )

    record = next(
        item for item in caplog.records if item.msg == "lineageweave.server_failure"
    )
    assert record.failure_outcome == "internal_error"
    assert "internal worker detail" not in caplog.text


def test_failure_at_attempt_limit_is_terminal_and_visible() -> None:
    connection = _Connection(values=[POST_CONTENT_MAX_ATTEMPTS])

    asyncio.run(
        post_content_worker._finish_failed_job(
            _Pool(connection),
            "00000000-0000-0000-0000-000000000001",
            failure_code="post_content_ingestion_failed",
            detail_text="provider outage",
            expected_attempt_count=POST_CONTENT_MAX_ATTEMPTS,
        )
    )

    updates = [args for query, args in connection.executed if "set status_code" in query]
    assert any(args[1] == FAILED and args[6] == "post_content_ingestion_attempt_limit" for args in updates)


def test_stale_worker_cannot_retry_after_lease_recovery() -> None:
    connection = _Connection(values=[2])

    asyncio.run(
        post_content_worker._finish_failed_job(
            _Pool(connection),
            "00000000-0000-0000-0000-000000000001",
            failure_code="post_content_ingestion_failed",
            detail_text="late provider failure",
            expected_attempt_count=1,
        )
    )

    assert not any("set status_code" in query for query, _args in connection.executed)


def test_stale_worker_cannot_mark_recovered_attempt_succeeded() -> None:
    class StaleConnection(_Connection):
        async def execute(self, query: str, *args: object) -> str:
            self.executed.append((query, args))
            return "UPDATE 0" if "update post_content_ingestion_job" in query else "OK"

    connection = StaleConnection()

    asyncio.run(
        post_content_worker._finish_job(
            _Pool(connection),
            "00000000-0000-0000-0000-000000000001",
            SUCCEEDED,
            expected_attempt_count=1,
        )
    )

    assert not any("insert into post_content_ingestion_job_status_event" in query for query, _args in connection.executed)


def test_recovery_enqueues_next_bounded_page_then_republishes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Every recovery cycle advances the durable candidate ledger once."""
    calls: list[tuple[str, object, object]] = []
    pool = object()
    client = object()

    async def enqueue(actual_pool: object, actual_client: object, **kwargs: object) -> None:
        calls.append(("enqueue", actual_pool, actual_client))
        assert kwargs == {
            "limit": 200,
            "require_embedding": True,
            "require_structure": True,
        }

    async def republish(
        actual_client: object, actual_pool: object, **kwargs: object
    ) -> object:
        calls.append(("republish", actual_pool, actual_client))
        assert kwargs == {"after_eligible_at": None, "after_post_id": None}
        return SimpleNamespace(next_eligible_at=None, next_post_id=None)

    monkeypatch.setattr(
        post_content_worker,
        "load_settings",
        lambda: SimpleNamespace(orchestrator_base_url="set", orchestrator_api_key="set"),
    )
    monkeypatch.setattr(post_content_worker, "enqueue_post_content_backfill", enqueue)
    monkeypatch.setattr(post_content_worker, "republish_queued_post_content_jobs", republish)

    asyncio.run(post_content_worker._recover_post_content_jobs(client, pool))

    assert calls == [("enqueue", pool, client), ("republish", pool, client)]


def test_recovery_republishes_after_candidate_selection_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A failed page selection cannot suppress recovery of queued jobs."""
    republished: list[bool] = []

    async def enqueue(*_args: object, **_kwargs: object) -> None:
        raise RuntimeError("synthetic database failure")

    async def republish(*_args: object, **_kwargs: object) -> None:
        republished.append(True)

    monkeypatch.setattr(
        post_content_worker,
        "load_settings",
        lambda: SimpleNamespace(orchestrator_base_url="", orchestrator_api_key=""),
    )
    monkeypatch.setattr(post_content_worker, "enqueue_post_content_backfill", enqueue)
    monkeypatch.setattr(post_content_worker, "republish_queued_post_content_jobs", republish)
    monkeypatch.setattr(post_content_worker, "record_server_failure", lambda *_a, **_k: None)

    asyncio.run(post_content_worker._recover_post_content_jobs(object(), object()))

    assert republished == [True]
