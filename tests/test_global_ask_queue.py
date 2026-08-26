"""Regressions for the Global Ask job queue's failure-settlement path."""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from datetime import UTC, datetime

from backend.app import global_ask_queue
from backend.app.global_ask_queue import load_job_visibility
from lineageweave import claim_verification as cv
from lineageweave.post_chat import ChatSourceDocument


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
        )
    )

    assert status_code == cv.VERIFICATION_COMPLETED
    assert results[0].source_post_ids == ("public-post",)
    assert results[0].evidence[0].url == "https://example.com/evidence"
    assert results[0].evidence[0].url not in results[0].source_post_ids


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
            )
        )

        assert status_code == cv.VERIFICATION_UNAVAILABLE
        assert results == ()


def test_public_verification_unavailable_next_action_is_product_facing() -> None:
    """Unavailable verification guides the reader without naming providers."""
    next_action = global_ask_queue._verification_next_action(
        cv.VERIFICATION_UNAVAILABLE
    )

    assert next_action == (
        "Review the internal citations now, then retry public verification when "
        "it is available."
    )
    assert "contextual-orchestrator" not in next_action


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
    assert failure_detail == (
        "Ask Agent is unavailable: contextual-orchestrator returned no complete evidence object"
    )


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
    assert settle_args[-1] == f"job exceeded the {global_ask_queue.JOB_DEADLINE_SECONDS}s deadline"


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
