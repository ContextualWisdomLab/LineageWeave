"""Regressions for the Global Ask job queue's failure-settlement path."""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from types import SimpleNamespace

import pytest

from backend.app import global_ask_queue
from backend.app.global_ask_queue import load_job_visibility


class _AvailableClient:
    available = True


class _Connection:
    def __init__(self, row: dict[str, object] | None) -> None:
        self.row = row
        self.executed: list[tuple[str, tuple[object, ...]]] = []

    async def fetchrow(self, *_args: object):
        return self.row

    async def execute(self, query: str, *args: object) -> str:
        self.executed.append((query, args))
        return "OK"


class _Pool:
    def __init__(self, connection: _Connection) -> None:
        self.connection = connection

    @asynccontextmanager
    async def acquire(self):
        yield self.connection


def _queued_row() -> dict[str, object]:
    return {
        "requesting_account_id": "00000000-0000-0000-0000-000000000001",
        "question_text": "What happened last week?",
        "verify_external_requested": False,
        "knowledge_cutoff": None,
    }


def test_question_embedding_finishes_before_global_ask_acquires_a_pool_slot(
    monkeypatch,
) -> None:
    """Provider latency must not consume the shared database pool."""
    connection = _Connection(None)

    class TrackingPool(_Pool):
        active = 0

        @asynccontextmanager
        async def acquire(self):
            self.active += 1
            try:
                yield self.connection
            finally:
                self.active -= 1

    pool = TrackingPool(connection)

    class EmbeddingClient:
        available = True
        resolved_model = "synthetic-embedding"

        def embed(self, _text: str) -> list[float]:
            assert pool.active == 0
            return [1.0, 0.0]

    class SemanticQueryClient:
        available = True

        def rewrite(self, _question: str) -> tuple[str, ...]:
            assert pool.active == 0
            return ("changed",)

    async def fake_gather(_conn, *_args, **kwargs):
        assert pool.active == 1
        assert kwargs["question_embedding"] == (
            [1.0, 0.0],
            "synthetic-embedding",
            1.0,
        )
        assert kwargs["search_phrases"] == ("changed",)
        return []

    monkeypatch.setattr(global_ask_queue, "gather_global_chat_sources", fake_gather)

    payload = asyncio.run(
        global_ask_queue.compute_global_ask_answer(
            pool,
            question_text="What changed?",
            corporate_entity_ids=set(),
            process_unit_ids=set(),
            process_scope_limited=False,
            chat_client=_AvailableClient(),
            embedding_client=EmbeddingClient(),
            semantic_query_client=SemanticQueryClient(),
        )
    )

    assert payload["source_post_ids"] == []
    assert pool.active == 0


def test_cutoff_global_ask_does_not_request_a_live_embedding(monkeypatch) -> None:
    """Cutoff retrieval must not call a channel it cannot use."""
    pool = _Pool(_Connection(None))

    class RejectEmbedding:
        available = True

        def embed(self, _text: str) -> list[float]:
            raise AssertionError("cutoff retrieval must not request an embedding")

    async def fake_gather(_conn, *_args, **kwargs):
        assert kwargs["question_embedding"] is None
        return []

    monkeypatch.setattr(global_ask_queue, "gather_global_chat_sources", fake_gather)

    payload = asyncio.run(
        global_ask_queue.compute_global_ask_answer(
            pool,
            question_text="What was known?",
            corporate_entity_ids=set(),
            process_unit_ids=set(),
            process_scope_limited=False,
            chat_client=_AvailableClient(),
            embedding_client=RejectEmbedding(),
            knowledge_cutoff=datetime(2026, 1, 15, tzinfo=UTC),
        )
    )

    assert payload["source_post_ids"] == []


def test_invalid_semantic_rewrite_retains_the_original_question(monkeypatch) -> None:
    """Malformed provider output degrades to the honest database query."""
    pool = _Pool(_Connection(None))

    class InvalidSemanticQueryClient:
        available = True

        def rewrite(self, _question: str) -> tuple[str, ...]:
            raise ValueError("invalid structured output")

    async def fake_gather(_conn, *_args, **kwargs):
        assert kwargs["search_phrases"] == ("What changed?",)
        return []

    monkeypatch.setattr(global_ask_queue, "gather_global_chat_sources", fake_gather)

    payload = asyncio.run(
        global_ask_queue.compute_global_ask_answer(
            pool,
            question_text="What changed?",
            corporate_entity_ids=set(),
            process_unit_ids=set(),
            process_scope_limited=False,
            chat_client=_AvailableClient(),
            semantic_query_client=InvalidSemanticQueryClient(),
        )
    )

    assert payload["source_post_ids"] == []


def test_unexpected_semantic_rewrite_error_retains_the_original_question(monkeypatch) -> None:
    """An unexpected optional-rewriter defect cannot fail the Ask job."""
    pool = _Pool(_Connection(None))

    class BrokenSemanticQueryClient:
        available = True

        def rewrite(self, _question: str) -> tuple[str, ...]:
            raise RuntimeError("unexpected provider envelope")

    async def fake_gather(_conn, *_args, **kwargs):
        assert kwargs["search_phrases"] == ("What changed?",)
        return []

    monkeypatch.setattr(global_ask_queue, "gather_global_chat_sources", fake_gather)

    payload = asyncio.run(
        global_ask_queue.compute_global_ask_answer(
            pool,
            question_text="What changed?",
            corporate_entity_ids=set(),
            process_unit_ids=set(),
            process_scope_limited=False,
            chat_client=_AvailableClient(),
            semantic_query_client=BrokenSemanticQueryClient(),
        )
    )

    assert payload["source_post_ids"] == []


def test_unavailable_question_embedding_is_not_called(monkeypatch) -> None:
    """An unavailable embedding is dropped while persisted evidence still runs."""
    connection = _Connection(None)
    pool = _Pool(connection)

    class UnavailableEmbedding:
        available = False
        resolved_model = None

        def embed(self, _text: str) -> list[float]:
            raise AssertionError("unavailable embedding must not be called")

    async def fake_gather(_conn, *_args, **kwargs):
        assert kwargs["question_embedding"] is None
        assert kwargs["embedding_client"].available is False
        return []

    monkeypatch.setattr(global_ask_queue, "gather_global_chat_sources", fake_gather)

    payload = asyncio.run(
        global_ask_queue.compute_global_ask_answer(
            pool,
            question_text="What changed?",
            corporate_entity_ids=set(),
            process_unit_ids=set(),
            process_scope_limited=False,
            chat_client=_AvailableClient(),
            embedding_client=UnavailableEmbedding(),
        )
    )

    assert payload["source_post_ids"] == []


def test_plain_answer_guides_the_reader_to_its_cited_evidence(monkeypatch) -> None:
    """A completed ordinary Ask answer always gives a useful next action."""
    source = SimpleNamespace(post_id="post-demo", historical_body_unavailable=False)

    async def fake_gather(*_args, **_kwargs):
        return [source]

    class ChatClient:
        def answer(self, *_args):
            return SimpleNamespace(
                answer_text="Synthetic answer", cited_post_ids=("post-demo",)
            )

    monkeypatch.setattr(global_ask_queue, "gather_global_chat_sources", fake_gather)
    monkeypatch.setattr(global_ask_queue, "cited_post_summaries", lambda *_args: [])
    monkeypatch.setattr(global_ask_queue, "cited_post_evidence", lambda *_args: [])

    async def empty_lineage(*_args):
        return {"nodes": [], "edges": [], "truncated": False}

    async def empty_images(*_args):
        return []

    monkeypatch.setattr(global_ask_queue, "lineage_graphs_for_posts", empty_lineage)
    monkeypatch.setattr(global_ask_queue, "cited_post_images", empty_images)

    payload = asyncio.run(
        global_ask_queue.compute_global_ask_answer(
            _Pool(_Connection(None)),
            question_text="What changed?",
            corporate_entity_ids=set(),
            process_unit_ids=set(),
            process_scope_limited=False,
            chat_client=ChatClient(),
        )
    )

    assert payload["next_action"] == "Open a cited post to review the evidence behind this answer."


def test_unexpected_job_failure_settles_with_a_generic_detail_not_the_raw_exception(
    monkeypatch,
) -> None:
    """Live bug (#361, reintroduced by the Valkey-queue restructuring): a raw
    orchestrator/provider exception once flowed straight into a client-visible
    field. `failure_detail` must never carry `str(exc)` -- only a bounded,
    generic message; the real exception is logged internally instead.
    """
    connection = _Connection(_queued_row())
    pool = _Pool(connection)
    secret_bearing_message = "upstream said: Bearer sk-super-secret-token-abc123 is invalid"

    async def _fake_load_job_visibility(_conn, _job_id, _account_id):
        return {"corp-1"}, set(), False, True

    async def _fake_compute_global_ask_answer(*_args, **_kwargs):
        raise ConnectionResetError(secret_bearing_message)

    monkeypatch.setattr(global_ask_queue, "load_job_visibility", _fake_load_job_visibility)
    monkeypatch.setattr(
        global_ask_queue, "compute_global_ask_answer", _fake_compute_global_ask_answer
    )

    asyncio.run(
        global_ask_queue.process_global_ask_job(
            pool,
            job_id="job-1",
            chat_factory=_AvailableClient,
        )
    )

    settle_query, settle_args = connection.executed[-1]
    assert "failure_detail" in settle_query
    failure_detail = settle_args[-1]
    assert secret_bearing_message not in failure_detail
    assert failure_detail == "Ask Agent could not complete this question. Try again later."


def test_permission_and_connection_errors_keep_their_pre_authored_safe_message(
    monkeypatch,
) -> None:
    """`PermissionError`/`ConnectionError` are raised locally with a
    pre-authored, safe message (permission state / missing config) -- unlike
    an arbitrary provider exception, `str(exc)` here is never a leak."""
    connection = _Connection(_queued_row())
    pool = _Pool(connection)

    async def _fake_load_job_visibility(_conn, _job_id, _account_id):
        return {"corp-1"}, set(), False, True

    async def _fake_compute_global_ask_answer(*_args, **_kwargs):
        raise global_ask_queue._SafeJobError("account lacks the post_read permission")

    monkeypatch.setattr(global_ask_queue, "load_job_visibility", _fake_load_job_visibility)
    monkeypatch.setattr(
        global_ask_queue, "compute_global_ask_answer", _fake_compute_global_ask_answer
    )

    asyncio.run(
        global_ask_queue.process_global_ask_job(
            pool,
            job_id="job-1",
            chat_factory=_AvailableClient,
        )
    )

    _settle_query, settle_args = connection.executed[-1]
    assert settle_args[-1] == "account lacks the post_read permission"


def test_job_deadline_timeout_settles_with_a_specific_but_still_generic_detail(
    monkeypatch,
) -> None:
    """A bare `asyncio.TimeoutError` (no message) still gets a useful,
    non-empty detail rather than an empty string."""
    connection = _Connection(_queued_row())
    pool = _Pool(connection)

    async def _fake_load_job_visibility(_conn, _job_id, _account_id):
        return {"corp-1"}, set(), False, True

    async def _fake_compute_global_ask_answer(*_args, **_kwargs):
        raise asyncio.TimeoutError()

    monkeypatch.setattr(global_ask_queue, "load_job_visibility", _fake_load_job_visibility)
    monkeypatch.setattr(
        global_ask_queue, "compute_global_ask_answer", _fake_compute_global_ask_answer
    )

    asyncio.run(
        global_ask_queue.process_global_ask_job(
            pool,
            job_id="job-1",
            chat_factory=_AvailableClient,
        )
    )

    _settle_query, settle_args = connection.executed[-1]
    assert settle_args[-1] == "Ask Agent took too long to answer. Try the question again."


def test_job_visibility_never_expands_past_queued_scope() -> None:
    """The worker uses stored scope rows, not every account affiliation."""

    class FakeConnection:
        async def fetch(self, query: str, *args):
            assert args == ("job-1", "account-1")
            if "corporate_entity_scope" in query:
                return [{"corporate_entity_id": "queued-entity"}]
            if "process_unit_scope" in query:
                return [{"process_unit_id": "queued-process"}]
            raise AssertionError(query)

        async def fetchval(self, query: str, *args):
            if "global_ask_job_process_unit_scope" in query:
                assert args == ("job-1",)
                return True
            assert "permission_code = 'post_read'" in query
            assert args == ("account-1",)
            return True

    entities, processes, process_scope_limited, has_post_read = asyncio.run(
        load_job_visibility(FakeConnection(), "job-1", "account-1")
    )

    assert entities == {"queued-entity"}
    assert processes == {"queued-process"}
    assert process_scope_limited is True
    assert has_post_read is True


def test_process_global_ask_job_forwards_opt_in_verify_external(monkeypatch) -> None:
    """Opt-in is persisted on the job row and must reach answer assembly."""
    connection = _Connection({**_queued_row(), "verify_external_requested": True})
    pool = _Pool(connection)
    captured: dict[str, object] = {}

    async def _fake_load_job_visibility(_conn, _job_id, _account_id):
        return {"corp-1"}, set(), False, True

    async def _fake_compute_global_ask_answer(*_args, **kwargs):
        captured.update(kwargs)
        return {
            "answer_text": "synthetic",
            "cited_post_ids": [],
            "cited_posts": [],
            "source_post_ids": [],
        }

    monkeypatch.setattr(global_ask_queue, "load_job_visibility", _fake_load_job_visibility)
    monkeypatch.setattr(
        global_ask_queue, "compute_global_ask_answer", _fake_compute_global_ask_answer
    )

    asyncio.run(
        global_ask_queue.process_global_ask_job(
            pool,
            job_id="job-1",
            chat_factory=_AvailableClient,
        )
    )

    assert captured["verify_external"] is True
    assert captured["claim_search_client"] is not None


def test_process_global_ask_job_does_not_build_search_client_without_opt_in(
    monkeypatch,
) -> None:
    """Ordinary Ask jobs must not initialize the unused public-search boundary."""
    connection = _Connection({**_queued_row(), "verify_external_requested": False})
    pool = _Pool(connection)
    captured: dict[str, object] = {}

    async def _fake_load_job_visibility(_conn, _job_id, _account_id):
        return {"corp-1"}, set(), False, True

    async def _fake_compute_global_ask_answer(*_args, **kwargs):
        captured.update(kwargs)
        return {"answer_text": "synthetic", "cited_post_ids": []}

    monkeypatch.setattr(global_ask_queue, "load_job_visibility", _fake_load_job_visibility)
    monkeypatch.setattr(
        global_ask_queue, "compute_global_ask_answer", _fake_compute_global_ask_answer
    )
    monkeypatch.setattr(
        global_ask_queue,
        "_public_claim_search_client",
        lambda: pytest.fail("search client must stay lazy when verification is off"),
    )

    asyncio.run(
        global_ask_queue.process_global_ask_job(
            pool,
            job_id="job-1",
            chat_factory=_AvailableClient,
        )
    )

    assert captured["verify_external"] is False
    assert captured["claim_search_client"] is None


def test_missing_public_claim_table_fails_startup_contract() -> None:
    """Application code must not hide a volume that has not replayed 0224."""
    import asyncpg

    class _MissingTable:
        async def fetch(self, *_args: object, **_kwargs: object):
            raise asyncpg.UndefinedTableError("public_claim_envelope")

    with pytest.raises(asyncpg.UndefinedTableError):
        asyncio.run(
            global_ask_queue.load_authorized_public_claim_envelopes(
                _MissingTable(), lambda _row: True
            )
        )


def test_public_claim_loader_drops_unauthorized_and_ineligible_rows() -> None:
    class _Rows:
        async def fetch(self, query: str, *_args: object, **_kwargs: object):
            assert "post.source_draft_code" in query
            assert "post.source_deleted_flag" in query
            return [
                {
                    "public_claim_envelope_id": "env-1",
                    "source_post_id": "post-demo-public",
                    "source_post_title": "Demo public post",
                    "claim_kind_code": "claim_organization_presence",
                    "subject_label": "Northridge Grid",
                    "claim_text": "Northridge Grid is a power utility.",
                    "truth_status_code": "truth_observed",
                    "event_occurred_at": None,
                    "egress_eligible": True,
                    "visibility_code": "public",
                    "corporate_entity_id": "corp-1",
                    "process_unit_id": "pu-1",
                },
                {
                    "public_claim_envelope_id": "env-hidden",
                    "source_post_id": "post-hidden",
                    "source_post_title": "Hidden post",
                    "claim_kind_code": "claim_organization_presence",
                    "subject_label": "Northridge Grid",
                    "claim_text": "should not dispatch",
                    "truth_status_code": "truth_observed",
                    "event_occurred_at": None,
                    "egress_eligible": True,
                    "visibility_code": "public",
                    "corporate_entity_id": "corp-hidden",
                    "process_unit_id": "pu-hidden",
                },
            ]

    envelopes = asyncio.run(
        global_ask_queue.load_authorized_public_claim_envelopes(
            _Rows(),
            lambda row: row["source_post_id"] == "post-demo-public",
        )
    )
    assert len(envelopes) == 1
    assert envelopes[0].source_post_id == "post-demo-public"


def test_public_claim_search_client_is_null_when_searxng_is_unset(monkeypatch) -> None:
    monkeypatch.setattr(
        "backend.app.config.load_settings",
        lambda: type("Settings", (), {"searxng_base_url": ""})(),
    )
    client = global_ask_queue._public_claim_search_client()
    assert client.available is False


def test_empty_sources_still_attach_opt_in_public_claim_verification(monkeypatch) -> None:
    class _PoolWithConn:
        @asynccontextmanager
        async def acquire(self):
            yield object()

    async def _no_sources(*_args, **_kwargs):
        return []

    async def _envelopes(*_args, **_kwargs):
        from lineageweave.public_claim_verification import (
            KIND_ORGANIZATION_PRESENCE,
            PublicClaimEnvelope,
        )

        return (
            PublicClaimEnvelope(
                public_claim_envelope_id="env-1",
                source_post_id="post-demo-public",
                source_post_title="Demo public post",
                claim_kind_code=KIND_ORGANIZATION_PRESENCE,
                subject_label="Northridge Grid",
                claim_text="Northridge Grid is a power utility named on the Demo public post.",
                truth_status_code="truth_observed",
                event_occurred_at=None,
                egress_eligible=True,
                visibility_code="public",
            ),
        )

    monkeypatch.setattr(global_ask_queue, "gather_global_chat_sources", _no_sources)
    monkeypatch.setattr(
        global_ask_queue, "load_authorized_public_claim_envelopes", _envelopes
    )
    payload = asyncio.run(
        global_ask_queue.compute_global_ask_answer(
            _PoolWithConn(),
            question_text="Does Northridge Grid exist?",
            corporate_entity_ids=set(),
            process_unit_ids=set(),
            process_scope_limited=False,
            chat_client=_AvailableClient(),
            verify_external=True,
        )
    )
    assert payload["public_claim_verification"]["status_code"] == "claim_unavailable"
    assert payload["public_claim_verification"]["claims"]
    assert payload["next_action"] == "No authorized source posts are available for this question."
    assert payload["public_claim_verification"]["next_action"]
