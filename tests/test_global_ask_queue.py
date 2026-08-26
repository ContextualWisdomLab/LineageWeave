"""Regressions for the Global Ask job queue's failure-settlement path."""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager

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


class _MalformedVerificationClient(_VerificationClient):
    def verify(self, claim: cv.PublicClaimCandidate) -> cv.ClaimVerificationResult:
        raise IndexError("empty provider choices")


def test_skipped_public_verification_does_not_nudge_the_reader() -> None:
    assert global_ask_queue._verification_next_action(cv.VERIFICATION_SKIPPED) is None


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
        external_claims=(
            cv.PublicClaimCandidate(
                "Project Apollo is public",
                "semantic_project",
                ("public-post",),
            ),
        ),
    )

    private_status, private_results = asyncio.run(
        global_ask_queue._verify_public_claims(
            [private_source],
            ["private-post"],
            verify_external=True,
            client=client,
        )
    )
    uncited_status, uncited_results = asyncio.run(
        global_ask_queue._verify_public_claims(
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
        external_claims=(
            cv.PublicClaimCandidate(
                "Project Apollo is public",
                "semantic_project",
                ("public-post",),
            ),
        ),
    )

    status_code, results = asyncio.run(
        global_ask_queue._verify_public_claims(
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


def test_malformed_provider_response_degrades_to_unavailable() -> None:
    source = cv.GlobalAskSourceDocument(
        "public-post",
        "Public",
        "Public body",
        external_claims=(
            cv.PublicClaimCandidate("A public claim", "semantic_project", ("public-post",)),
        ),
    )
    status_code, results = asyncio.run(
        global_ask_queue._verify_public_claims(
            [source],
            ["public-post"],
            verify_external=True,
            client=_MalformedVerificationClient(),
        )
    )
    assert status_code == cv.VERIFICATION_UNAVAILABLE
    assert results == ()


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
