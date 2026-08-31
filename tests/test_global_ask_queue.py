"""Regressions for the Global Ask job queue's failure-settlement path."""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from types import SimpleNamespace

import pytest

from backend.app import global_ask_queue
from backend.app.global_ask_queue import load_job_visibility
from lineageweave import claim_verification as cv
from lineageweave.post_chat import ChatAnswer, ChatSourceDocument
from lineageweave.public_claim_envelope import PersistedPublicClaimEnvelope


class _AvailableClient:
    available = True


def test_public_claim_load_deduplicates_resource_bindings() -> None:
    """A duplicate resource binding must not duplicate one admitted envelope."""
    sql = global_ask_queue._AUTHORIZED_PUBLIC_CLAIM_ENVELOPES_SQL.casefold()
    assert "exists (" in sql
    assert "from provenance_resource_binding evidence" in sql
    assert "join provenance_resource_binding evidence" not in sql


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


def test_worker_reprepares_when_embedding_model_identity_changes(monkeypatch) -> None:
    """A discovered model replacement closes readiness and prepares before dispatch."""

    class IdentityConnection:
        async def fetch(self, query: str, model_identity: str):
            assert "embedding_dimension_count" in query
            return [
                {
                    "embedding_dimension_count": (
                        2 if model_identity == "synthetic-model-a" else 3
                    )
                }
            ]

    class ExactIndex:
        def __init__(self) -> None:
            self.prepared: list[tuple[str, int]] = []
            self.bound_pool = None

        def _bind_pool(self, pool) -> None:
            self.bound_pool = pool

        async def prepare(self, _conn, *, model_identity, vector_dimension) -> None:
            self.prepared.append((model_identity, vector_dimension))

        async def is_prepared_for(self, _conn, **_identity) -> bool:
            return True

    models = iter(("synthetic-model-a", "synthetic-model-b"))

    def embedding_factory():
        return SimpleNamespace(
            available=True,
            resolved_model=next(models),
            batch_capabilities=lambda: None,
        )

    exact_index = ExactIndex()
    pool = _Pool(IdentityConnection())
    readiness = asyncio.Event()
    invalidations = 0

    def invalidate(ready: asyncio.Event) -> None:
        nonlocal invalidations
        invalidations += 1
        ready.clear()

    async def stream_tail(_client) -> str:
        return "0-0"

    async def republish(_client, _pool) -> None:
        return None

    async def consume(*_args, **_kwargs) -> str:
        assert exact_index.prepared == [
            ("synthetic-model-a", 2),
            ("synthetic-model-b", 3),
        ]
        assert readiness.is_set()
        raise asyncio.CancelledError

    monkeypatch.setattr(global_ask_queue, "invalidate_worker_readiness", invalidate)
    monkeypatch.setattr(global_ask_queue, "_stream_tail", stream_tail)
    monkeypatch.setattr(
        global_ask_queue, "republish_queued_global_ask_jobs", republish
    )
    monkeypatch.setattr(global_ask_queue, "consume_global_ask_stream_once", consume)

    with pytest.raises(asyncio.CancelledError):
        asyncio.run(
            global_ask_queue.run_global_ask_worker(
                object(),
                pool,
                chat_factory=_AvailableClient,
                embedding_factory=embedding_factory,
                exact_semantic_index=exact_index,
                readiness=readiness,
            )
        )

    assert exact_index.bound_pool is pool
    assert invalidations == 1


def test_worker_prepares_empty_corpus_then_reprepares_first_embedding(
    monkeypatch,
) -> None:
    """A fresh database consumes work and replaces its empty exact snapshot."""

    class IdentityConnection:
        def __init__(self) -> None:
            self.fetches = 0

        async def fetch(self, query: str, model_identity: str):
            assert "embedding_dimension_count" in query
            assert model_identity == "synthetic-model"
            self.fetches += 1
            return [] if self.fetches == 1 else [{"embedding_dimension_count": 2}]

    class ExactIndex:
        def __init__(self) -> None:
            self.prepared: list[tuple[str, int]] = []

        def _bind_pool(self, _pool) -> None:
            return None

        async def prepare(self, _conn, *, model_identity, vector_dimension) -> None:
            self.prepared.append((model_identity, vector_dimension))

        async def is_prepared_for(self, _conn, **_identity) -> bool:
            return True

    def embedding_factory():
        return SimpleNamespace(
            available=True,
            resolved_model="synthetic-model",
            batch_capabilities=lambda: None,
        )

    exact_index = ExactIndex()
    pool = _Pool(IdentityConnection())
    readiness = asyncio.Event()
    invalidations = 0

    def invalidate(ready: asyncio.Event) -> None:
        nonlocal invalidations
        invalidations += 1
        ready.clear()

    async def stream_tail(_client) -> str:
        return "0-0"

    async def republish(_client, _pool) -> None:
        return None

    async def consume(*_args, **_kwargs) -> str:
        assert exact_index.prepared == [
            ("synthetic-model", 0),
            ("synthetic-model", 2),
        ]
        assert readiness.is_set()
        raise asyncio.CancelledError

    monkeypatch.setattr(global_ask_queue, "invalidate_worker_readiness", invalidate)
    monkeypatch.setattr(global_ask_queue, "_stream_tail", stream_tail)
    monkeypatch.setattr(
        global_ask_queue, "republish_queued_global_ask_jobs", republish
    )
    monkeypatch.setattr(global_ask_queue, "consume_global_ask_stream_once", consume)

    with pytest.raises(asyncio.CancelledError):
        asyncio.run(
            global_ask_queue.run_global_ask_worker(
                object(),
                pool,
                chat_factory=_AvailableClient,
                embedding_factory=embedding_factory,
                exact_semantic_index=exact_index,
                readiness=readiness,
            )
        )

    assert invalidations == 1


def test_worker_restores_readiness_after_identity_discovery_recovers(
    monkeypatch,
) -> None:
    """A transient discovery failure cannot strand a prepared worker unready."""

    class IdentityConnection:
        async def fetch(self, query: str, model_identity: str):
            assert "embedding_dimension_count" in query
            assert model_identity == "synthetic-model"
            return [{"embedding_dimension_count": 2}]

    class ExactIndex:
        def __init__(self) -> None:
            self.prepared = 0

        def _bind_pool(self, _pool) -> None:
            return None

        async def prepare(self, _conn, **_identity) -> None:
            self.prepared += 1

        async def is_prepared_for(self, _conn, **_identity) -> bool:
            return True

    discoveries = iter(("available", "unavailable", "available"))

    def embedding_factory():
        available = next(discoveries) == "available"
        return SimpleNamespace(
            available=available,
            resolved_model="synthetic-model" if available else None,
            batch_capabilities=lambda: None,
        )

    exact_index = ExactIndex()
    pool = _Pool(IdentityConnection())
    readiness = asyncio.Event()
    invalidations = 0

    def invalidate(ready: asyncio.Event) -> None:
        nonlocal invalidations
        invalidations += 1
        ready.clear()

    async def sleep(_seconds: float) -> None:
        assert not readiness.is_set()

    async def stream_tail(_client) -> str:
        return "0-0"

    async def republish(_client, _pool) -> None:
        return None

    async def consume(*_args, **_kwargs) -> str:
        assert readiness.is_set()
        raise asyncio.CancelledError

    monkeypatch.setattr(global_ask_queue, "invalidate_worker_readiness", invalidate)
    monkeypatch.setattr(global_ask_queue.asyncio, "sleep", sleep)
    monkeypatch.setattr(global_ask_queue, "_stream_tail", stream_tail)
    monkeypatch.setattr(
        global_ask_queue, "republish_queued_global_ask_jobs", republish
    )
    monkeypatch.setattr(global_ask_queue, "consume_global_ask_stream_once", consume)

    with pytest.raises(asyncio.CancelledError):
        asyncio.run(
            global_ask_queue.run_global_ask_worker(
                object(),
                pool,
                chat_factory=_AvailableClient,
                embedding_factory=embedding_factory,
                exact_semantic_index=exact_index,
                readiness=readiness,
            )
        )

    assert exact_index.prepared == 1
    assert invalidations == 1


def _queued_row() -> dict[str, object]:
    return {
        "requesting_account_id": "00000000-0000-0000-0000-000000000001",
        "question_text": "What happened last week?",
        "verify_external_requested": False,
        "knowledge_cutoff": None,
    }


class _VerificationClient:
    available = True

    def __init__(self) -> None:
        self.calls = 0

    def verify(self, claim: cv.PublicClaimCandidate) -> cv.ClaimVerificationResult:
        self.calls += 1
        return cv.ClaimVerificationResult(
            claim_text=claim.claim_text,
            claim_kind=claim.claim_kind,
            status_code=cv.CLAIM_SUPPORTED,
            rationale="Public evidence supports this claim.",
            source_post_ids=claim.source_post_ids,
            evidence=(
                cv.ExternalEvidenceDocument(
                    "Public source", "https://example.com/evidence", "Evidence"
                ),
            ),
        )


def test_public_verification_requires_public_capability_and_internal_citation() -> None:
    """Private facts and uncited public facts never reach external search."""

    client = _VerificationClient()
    private_source = ChatSourceDocument(
        "private-post",
        "Private",
        "Private body",
        evidence_facts=("project: Apollo | evidence: private",),
    )
    public_source = cv.GlobalAskSourceDocument(
        "public-post",
        "Public",
        "Public body",
        external_claim_facts=("project: Apollo | evidence: public",),
    )

    private_status, private_results = asyncio.run(
        global_ask_queue._verify_public_claims(
            "Apollo",
            [private_source],
            ["private-post"],
            verify_external=True,
            client=client,
        )
    )
    uncited_status, uncited_results = asyncio.run(
        global_ask_queue._verify_public_claims(
            "Apollo",
            [public_source],
            [],
            verify_external=True,
            client=client,
        )
    )

    assert private_status == cv.VERIFICATION_NO_PUBLIC_CLAIMS
    assert uncited_status == cv.VERIFICATION_NO_PUBLIC_CLAIMS
    assert private_results == uncited_results == ()
    assert client.calls == 0


def test_no_public_claim_next_action_opens_authorized_evidence() -> None:
    """Customer copy names the evidence action, not an internal boundary."""

    next_action = global_ask_queue._verification_next_action(
        cv.VERIFICATION_NO_PUBLIC_CLAIMS
    )

    assert next_action == "Ask about a specific claim or narrow the time range, then retry."
    assert "internal" not in next_action.lower()


def test_unavailable_public_verification_guides_the_reader_without_service_names() -> None:
    """Unavailable verification names the customer action, not its providers."""

    next_action = global_ask_queue._verification_next_action(
        cv.VERIFICATION_UNAVAILABLE
    )

    assert next_action == (
        "Ask a workspace administrator to enable public verification, then retry."
    )
    assert "orchestrator" not in next_action.lower()


def test_public_verification_keeps_external_urls_out_of_internal_citations() -> None:
    """A verified URL remains external evidence, never a cited post id."""

    client = _VerificationClient()
    source = cv.GlobalAskSourceDocument(
        "public-post",
        "Public",
        "Public body",
        external_claim_facts=("project: Apollo | evidence: public",),
    )

    status_code, results = asyncio.run(
        global_ask_queue._verify_public_claims(
            "Apollo",
            [source],
            ["public-post"],
            verify_external=True,
            client=client,
            persisted_envelopes=(
                PersistedPublicClaimEnvelope(
                    public_claim_envelope_id="envelope-1",
                    source_post_id="public-post",
                    claim_kind_code="claim_public_event",
                    claim_text="Synthetic public event.",
                ),
            ),
        )
    )

    assert status_code == cv.VERIFICATION_COMPLETED
    assert results[0].source_post_ids == ("public-post",)
    assert results[0].evidence[0].url == "https://example.com/evidence"
    assert results[0].evidence[0].url not in results[0].source_post_ids


def test_persisted_envelope_is_production_admission_not_question_overlap() -> None:
    """A stored cited envelope reaches the verifier without token nomination."""

    client = _VerificationClient()
    envelope = PersistedPublicClaimEnvelope(
        public_claim_envelope_id="envelope-1",
        source_post_id="public-post",
        claim_kind_code="claim_public_event",
        claim_text="Synthetic launch happened.",
    )

    status_code, results = asyncio.run(
        global_ask_queue._verify_public_claims(
            "A question with no overlapping words",
            [],
            ["public-post"],
            verify_external=True,
            client=client,
            persisted_envelopes=(envelope,),
        )
    )

    assert status_code == cv.VERIFICATION_COMPLETED
    assert results[0].claim_text == "Synthetic launch happened."
    assert results[0].source_post_ids == ("public-post",)


def test_omitted_persisted_envelopes_fail_closed_without_token_overlap() -> None:
    """A future caller cannot restore legacy question-token nomination."""
    client = _VerificationClient()
    source = cv.GlobalAskSourceDocument(
        "public-post",
        "Synthetic launch",
        "Synthetic launch happened.",
        external_claim_facts=("event: Synthetic launch | evidence: public",),
    )

    status_code, results = asyncio.run(
        global_ask_queue._verify_public_claims(
            "When did the Synthetic launch happen?",
            [source],
            ["public-post"],
            verify_external=True,
            client=client,
        )
    )

    assert status_code == cv.VERIFICATION_NO_PUBLIC_CLAIMS
    assert results == ()
    assert client.calls == 0


def test_persisted_envelope_must_name_a_cited_post() -> None:
    """A stored but uncited envelope never crosses the public verifier."""

    client = _VerificationClient()
    envelope = PersistedPublicClaimEnvelope(
        public_claim_envelope_id="envelope-1",
        source_post_id="other-public-post",
        claim_kind_code="claim_public_relationship",
        claim_text="Synthetic organizations announced a relationship.",
    )

    status_code, results = asyncio.run(
        global_ask_queue._verify_public_claims(
            "relationship",
            [],
            ["cited-public-post"],
            verify_external=True,
            client=client,
            persisted_envelopes=(envelope,),
        )
    )

    assert status_code == cv.VERIFICATION_NO_PUBLIC_CLAIMS
    assert results == ()
    assert client.calls == 0


def test_malformed_public_verification_is_unavailable() -> None:
    """Malformed provider/search envelopes do not discard a completed answer."""
    source = cv.GlobalAskSourceDocument(
        "public-post",
        "Public",
        "Public body",
        external_claim_facts=("project: Apollo | evidence: public",),
    )

    for error in (
        IndexError("empty choices"),
        AttributeError("invalid search body"),
        RuntimeError("provider adapter failed"),
    ):
        class MalformedClient:
            available = True

            def verify(self, _claim):
                raise error

        status_code, results = asyncio.run(
            global_ask_queue._verify_public_claims(
                "Apollo",
                [source],
                ["public-post"],
                verify_external=True,
                client=MalformedClient(),
                persisted_envelopes=(
                    PersistedPublicClaimEnvelope(
                        public_claim_envelope_id="envelope-1",
                        source_post_id="public-post",
                        claim_kind_code="claim_public_event",
                        claim_text="Synthetic public event.",
                    ),
                ),
            )
        )

        assert status_code == cv.VERIFICATION_UNAVAILABLE
        assert results == ()


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
    assert payload["cited_source_references"] == []
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
    assert failure_detail == global_ask_queue._ASK_RETRY_MESSAGE


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
    assert settle_args[-1] == global_ask_queue._ASK_RETRY_MESSAGE


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


def test_completed_answer_carries_the_cited_source_clock(monkeypatch) -> None:
    """The UI timeline receives the admitted source clock, not a graph guess."""
    connection = _Connection(None)
    pool = _Pool(connection)
    sources = [
        ChatSourceDocument(
            "post-1",
            "Synthetic event",
            "body",
            observed_at="2026-08-21T03:00:00+00:00",
            time_axis_code="event_occurred_at",
        )
    ]

    async def _fake_gather(*_args, **_kwargs):
        return sources

    async def _fake_graph(*_args, **_kwargs):
        return {"nodes": [], "edges": [], "truncated": False}

    async def _fake_images(*_args, **_kwargs):
        return []

    async def _fake_source_references(*_args, **_kwargs):
        return [{
            "post_id": "post-1",
            "lead_kind_code": "research_lead_semantic_unit",
            "evidence_url": "https://example.com/source",
            "evidence_title_text": "Public source",
            "evidence_excerpt_text": "Public excerpt",
            "judgment_code": "research_supported",
            "next_action_text": "Compare the public source with the cited post.",
            "checked_at": "2026-08-20T00:00:00Z",
        }]

    class _AnswerClient:
        def answer(self, _question, _sources):
            return ChatAnswer("Grounded answer", ("post-1",))

    monkeypatch.setattr(global_ask_queue, "gather_global_chat_sources", _fake_gather)
    monkeypatch.setattr(global_ask_queue, "lineage_graphs_for_posts", _fake_graph)
    monkeypatch.setattr(global_ask_queue, "cited_post_images", _fake_images)
    monkeypatch.setattr(
        global_ask_queue,
        "list_ask_source_references",
        _fake_source_references,
    )

    payload = asyncio.run(
        global_ask_queue.compute_global_ask_answer(
            pool,
            question_text="What happened?",
            corporate_entity_ids=set(),
            process_unit_ids=set(),
            process_scope_limited=False,
            chat_client=_AnswerClient(),
        )
    )

    assert payload["cited_events"] == [
        {
            "post_id": "post-1",
            "post_title": "Synthetic event",
            "observed_at": "2026-08-21T03:00:00+00:00",
            "time_axis_code": "event_occurred_at",
        }
    ]
    assert payload["cited_source_references"][0]["evidence_url"] == (
        "https://example.com/source"
    )
    assert payload["delivery"]["report"]["source_documents"][0][
        "source_references"
    ][0]["title"] == "Public source"
