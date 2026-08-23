"""Contracts for project histories attached to post-scoped and Global Ask."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import UUID

import pytest
from fastapi import HTTPException

from backend.app import main
from backend.app.ask_project_history import (
    AskEvidenceConnection,
    AskEvidenceBatchLimitError,
    AskEvidenceProjection,
    POST_ASK_HISTORY_EXCHANGE_LIMIT,
    ask_knowledge_cutoff,
    global_ask_session_citations_authorized,
    read_authorized_ask_evidence,
    read_authorized_ask_evidence_batch,
)
from backend.app.auth import CurrentAccount
from backend.app.post_chat_ingestion import (
    PostChatHistoryLimitError,
    gather_global_chat_sources,
)

CUTOFF = datetime(2026, 8, 20, 12, 0, tzinfo=UTC)


class _EvidenceConnection:
    """Query-shaped double for current citation and project evidence."""

    def __init__(self, rows: list[dict[str, object]]) -> None:
        self.rows = rows
        self.calls: list[tuple[str, tuple[object, ...]]] = []

    async def fetch(self, query: str, *args: object):
        self.calls.append((query, args))
        if "citation_request as materialized" in query:
            return [dict(row, exchange_ordinal=row.get("exchange_ordinal", 1)) for row in self.rows]
        return self.rows


def test_ask_evidence_protocol_and_cutoff_validation_contracts() -> None:
    with pytest.raises(NotImplementedError):
        asyncio.run(AskEvidenceConnection.fetch(None, "select 1"))
    assert ask_knowledge_cutoff("2026-08-20T12:00:00Z") == CUTOFF
    assert ask_knowledge_cutoff("2026-08-20T21:00:00+09:00") == CUTOFF
    with pytest.raises(ValueError, match="ISO-8601"):
        ask_knowledge_cutoff("not-a-clock")
    with pytest.raises(ValueError, match="datetime or ISO-8601"):
        ask_knowledge_cutoff(3)
    with pytest.raises(ValueError, match="include an offset"):
        ask_knowledge_cutoff(datetime(2026, 8, 20, 12, 0))


def test_authorized_ask_evidence_groups_exact_projects_and_preserves_citation_order() -> None:
    conn = _EvidenceConnection(
        [
            {
                "post_id": "00000000-0000-4000-8000-000000000002",
                "post_title": "Second evidence",
                "citation_ordinal": 2,
                "project_key": "P-100",
                "project_name": "Synthetic renewal",
                "truth_status_code": "inferred",
                "truth_order": 1,
            },
            {
                "post_id": "00000000-0000-4000-8000-000000000001",
                "post_title": "First evidence",
                "citation_ordinal": 1,
                "project_key": "P-100",
                "project_name": "Synthetic renewal",
                "truth_status_code": "observed",
                "truth_order": 0,
            },
        ]
    )

    result = asyncio.run(
        read_authorized_ask_evidence(
            conn,
            cited_post_ids=[
                "00000000-0000-4000-8000-000000000001",
                "00000000-0000-4000-8000-000000000002",
            ],
            corporate_entity_ids=["tenant-a"],
            knowledge_cutoff=CUTOFF,
        )
    )

    assert result.all_citations_visible
    assert [post["post_title"] for post in result.cited_posts] == [
        "First evidence",
        "Second evidence",
    ]
    assert result.project_histories == (
        {
            "project_key": "P-100",
            "project_name": "Synthetic renewal",
            "focus_post_id": "00000000-0000-4000-8000-000000000001",
            "source_post_ids": [
                "00000000-0000-4000-8000-000000000001",
                "00000000-0000-4000-8000-000000000002",
            ],
            "knowledge_cutoff": "2026-08-20T12:00:00Z",
            "truth_status_code": "observed",
        },
    )
    query, args = conn.calls[0]
    assert "source_draft_code" in query
    assert "source_deleted_flag" in query
    assert "created_at <= citation_request.knowledge_cutoff" in query
    assert list(args[3]) == [CUTOFF, CUTOFF]


def test_authorized_ask_evidence_fails_closed_when_any_citation_is_hidden() -> None:
    conn = _EvidenceConnection(
        [
            {
                "post_id": "00000000-0000-4000-8000-000000000001",
                "post_title": "Visible evidence",
                "citation_ordinal": 1,
                "project_key": None,
                "project_name": None,
                "truth_status_code": None,
                "truth_order": None,
            }
        ]
    )

    result = asyncio.run(
        read_authorized_ask_evidence(
            conn,
            cited_post_ids=[
                "00000000-0000-4000-8000-000000000001",
                "00000000-0000-4000-8000-000000000099",
            ],
            corporate_entity_ids=["tenant-a"],
            knowledge_cutoff=CUTOFF,
        )
    )

    assert not result.all_citations_visible
    assert result.project_histories == ()


def test_authorized_ask_evidence_ignores_unrequested_and_invalid_project_rows() -> None:
    first_id = "00000000-0000-4000-8000-000000000001"
    second_id = "00000000-0000-4000-8000-000000000002"
    conn = _EvidenceConnection(
        [
            {
                "post_id": "00000000-0000-4000-8000-000000000099",
                "post_title": "Unrequested",
                "citation_ordinal": 99,
                "project_key": None,
                "project_name": None,
                "truth_status_code": None,
                "truth_order": None,
            },
            {
                "post_id": first_id,
                "post_title": "First",
                "citation_ordinal": 1,
                "project_key": "",
                "project_name": "Invalid project",
                "truth_status_code": "inferred",
                "truth_order": 2,
            },
            {
                "post_id": first_id,
                "post_title": "First",
                "citation_ordinal": 1,
                "project_key": "P-1",
                "project_name": "Inferred project",
                "truth_status_code": "inferred",
                "truth_order": 1,
            },
            {
                "post_id": second_id,
                "post_title": "Second",
                "citation_ordinal": 2,
                "project_key": "p-1",
                "project_name": "Observed project",
                "truth_status_code": "observed",
                "truth_order": 0,
            },
            {
                "post_id": second_id,
                "post_title": "Second",
                "citation_ordinal": 2,
                "project_key": "P-1",
                "project_name": "Later duplicate",
                "truth_status_code": "inferred",
                "truth_order": 2,
            },
        ]
    )

    result = asyncio.run(
        read_authorized_ask_evidence(
            conn,
            cited_post_ids=[first_id, second_id],
            corporate_entity_ids=["tenant-a"],
            knowledge_cutoff=CUTOFF,
        )
    )

    assert result.all_citations_visible
    assert result.project_histories[0]["project_name"] == "Observed project"
    assert result.project_histories[0]["truth_status_code"] == "observed"
    assert result.project_histories[0]["source_post_ids"] == [first_id, second_id]


def test_authorized_ask_evidence_rejects_non_uuid_citations_before_sql() -> None:
    with pytest.raises(ValueError, match="UUIDs"):
        asyncio.run(
            read_authorized_ask_evidence(
                _EvidenceConnection([]),
                cited_post_ids=["not-a-uuid"],
                corporate_entity_ids=["tenant-a"],
                knowledge_cutoff=CUTOFF,
            )
        )


class _GeneratedEvidenceConnection:
    """Build deterministic visible rows from the flattened batch arguments."""

    def __init__(self, hidden_ids: set[str] | None = None) -> None:
        self.hidden_ids = hidden_ids or set()
        self.calls: list[tuple[str, tuple[object, ...]]] = []

    async def fetch(self, query: str, *args: object):
        self.calls.append((query, args))
        exchange_ordinals, citation_ordinals, citation_ids, _cutoffs, _tenants = args
        return [
            {
                "exchange_ordinal": exchange_ordinal,
                "citation_ordinal": citation_ordinal,
                "post_id": post_id,
                "post_title": f"Evidence {post_id}",
                "project_key": f"P-{post_id[-2:]}",
                "project_name": f"Synthetic project {post_id[-2:]}",
                "truth_status_code": "observed",
                "truth_order": 0,
            }
            for exchange_ordinal, citation_ordinal, post_id in zip(
                exchange_ordinals,
                citation_ordinals,
                citation_ids,
                strict=True,
            )
            if post_id not in self.hidden_ids
        ]


@pytest.mark.parametrize("exchange_count", [1, 10, POST_ASK_HISTORY_EXCHANGE_LIMIT])
def test_batch_evidence_matches_sequential_projection_at_supported_sizes(
    exchange_count: int,
) -> None:
    exchanges = [
        ([str(UUID(int=index + 1))], CUTOFF)
        for index in range(exchange_count)
    ]
    batch_connection = _GeneratedEvidenceConnection()
    batch = asyncio.run(
        read_authorized_ask_evidence_batch(
            batch_connection,
            exchanges=exchanges,
            corporate_entity_ids=["tenant-a"],
        )
    )
    sequential_connection = _GeneratedEvidenceConnection()

    async def sequential() -> tuple[AskEvidenceProjection, ...]:
        return tuple(
            [
                await read_authorized_ask_evidence(
                    sequential_connection,
                    cited_post_ids=citations,
                    corporate_entity_ids=["tenant-a"],
                    knowledge_cutoff=cutoff,
                )
                for citations, cutoff in exchanges
            ]
        )

    assert batch == asyncio.run(sequential())
    assert len(batch_connection.calls) == 1
    assert len(sequential_connection.calls) == exchange_count


def test_batch_evidence_partitions_hidden_citation_and_mixed_cutoffs() -> None:
    visible_id = "00000000-0000-4000-8000-000000000001"
    hidden_id = "00000000-0000-4000-8000-000000000099"
    later_cutoff = datetime(2026, 8, 21, 12, 0, tzinfo=UTC)
    connection = _GeneratedEvidenceConnection({hidden_id})

    result = asyncio.run(
        read_authorized_ask_evidence_batch(
            connection,
            exchanges=[([visible_id], CUTOFF), ([hidden_id], later_cutoff)],
            corporate_entity_ids=["tenant-a"],
        )
    )

    assert result[0].all_citations_visible
    assert not result[1].all_citations_visible
    assert result[1].cited_posts == ()
    assert result[1].project_histories == ()
    _query, args = connection.calls[0]
    assert list(args[3]) == [CUTOFF, later_cutoff]


def test_batch_evidence_validates_all_bounds_before_sql() -> None:
    connection = _GeneratedEvidenceConnection()
    citation_ids = [str(UUID(int=index + 1)) for index in range(65)]

    with pytest.raises(ValueError, match="UUIDs"):
        asyncio.run(
            read_authorized_ask_evidence_batch(
                connection,
                exchanges=[(["not-a-uuid"], CUTOFF)],
                corporate_entity_ids=["tenant-a"],
            )
        )
    with pytest.raises(AskEvidenceBatchLimitError, match="exchange count"):
        asyncio.run(
            read_authorized_ask_evidence_batch(
                connection,
                exchanges=[([], CUTOFF)] * (POST_ASK_HISTORY_EXCHANGE_LIMIT + 1),
                corporate_entity_ids=["tenant-a"],
            )
        )
    with pytest.raises(AskEvidenceBatchLimitError, match="citation count"):
        asyncio.run(
            read_authorized_ask_evidence_batch(
                connection,
                exchanges=[(citation_ids, CUTOFF)],
                corporate_entity_ids=["tenant-a"],
            )
        )
    with pytest.raises(AskEvidenceBatchLimitError, match="history citation count"):
        asyncio.run(
            read_authorized_ask_evidence_batch(
                connection,
                exchanges=[(citation_ids, CUTOFF)] * 4,
                corporate_entity_ids=["tenant-a"],
                maximum_exchange_citations=65,
            )
        )
    assert connection.calls == []


def test_batch_evidence_skips_sql_when_every_exchange_has_no_citations() -> None:
    connection = _GeneratedEvidenceConnection()

    result = asyncio.run(
        read_authorized_ask_evidence_batch(
            connection,
            exchanges=[([], CUTOFF), ([], CUTOFF)],
            corporate_entity_ids=["tenant-a"],
        )
    )

    assert len(result) == 2
    assert all(projection.all_citations_visible for projection in result)
    assert connection.calls == []

    assert (
        asyncio.run(
            read_authorized_ask_evidence_batch(
                connection,
                exchanges=[],
                corporate_entity_ids=["tenant-a"],
            )
        )
        == ()
    )


def test_global_ask_session_reauthorizes_every_persisted_citation() -> None:
    class SessionConnection:
        def __init__(self) -> None:
            self.call = 0

        async def fetch(self, query: str, *args: object):
            del args
            self.call += 1
            if "global_ask_turn_citation" in query:
                return [
                    {"cited_post_id": "00000000-0000-4000-8000-000000000001"},
                    {"cited_post_id": "00000000-0000-4000-8000-000000000099"},
                ]
            return [
                {
                    "exchange_ordinal": 1,
                    "post_id": "00000000-0000-4000-8000-000000000001",
                    "post_title": "Visible evidence",
                    "citation_ordinal": 1,
                    "project_key": None,
                    "project_name": None,
                    "truth_status_code": None,
                    "truth_order": None,
                }
            ]

    authorized = asyncio.run(
        global_ask_session_citations_authorized(
            SessionConnection(),
            session_id="00000000-0000-4000-8000-000000000010",
            corporate_entity_ids=["tenant-a"],
            knowledge_cutoff=CUTOFF,
        )
    )
    assert not authorized


def test_global_ask_session_fails_closed_before_reauthorizing_overflow() -> None:
    class OverflowConnection:
        def __init__(self) -> None:
            self.calls = 0

        async def fetch(self, _query: str, *_args: object):
            self.calls += 1
            return [
                {"cited_post_id": str(UUID(int=index + 1))}
                for index in range(257)
            ]

    connection = OverflowConnection()
    authorized = asyncio.run(
        global_ask_session_citations_authorized(
            connection,
            session_id="00000000-0000-4000-8000-000000000010",
            corporate_entity_ids=["tenant-a"],
            knowledge_cutoff=CUTOFF,
        )
    )

    assert not authorized
    assert connection.calls == 1


def test_global_source_retrieval_applies_cutoff_and_publication_eligibility() -> None:
    calls: list[tuple[str, tuple[object, ...]]] = []

    class CaptureConnection:
        async def fetch(self, query: str, *args: object):
            calls.append((query, args))
            return []

    asyncio.run(
        gather_global_chat_sources(
            CaptureConnection(),
            lambda _row: True,
            ["tenant-a"],
            question="synthetic project",
            limit=2,
            knowledge_cutoff=CUTOFF,
        )
    )

    candidate_queries = [query for query, _args in calls if "matched_in" in query]
    source_calls = [
        (query, args)
        for query, args in calls
        if "array_position($2::uuid[], post_id)" in query
    ]
    assert candidate_queries
    assert all("source_draft_code" in query and "created_at <= $3" in query for query in candidate_queries)
    assert source_calls
    source_query, source_args = source_calls[0]
    assert "source_deleted_flag" in source_query
    assert "created_at <= $4" in source_query
    assert len(source_args) == 4
    assert list(source_args[0]) == ["tenant-a"]
    assert source_args[3] == CUTOFF


class _Acquire:
    def __init__(self, connection: object) -> None:
        self.connection = connection

    async def __aenter__(self) -> object:
        return self.connection

    async def __aexit__(self, exc_type, exc_value, traceback) -> None:
        return None


class _Pool:
    def __init__(self, connection: object) -> None:
        self.connection = connection

    def acquire(self) -> _Acquire:
        return _Acquire(self.connection)


def _account() -> CurrentAccount:
    return CurrentAccount(
        user_account_id="account-1",
        external_subject_id="subject-1",
        display_name="Synthetic analyst",
        preferred_locale="en",
        corporate_entity_ids=frozenset({"tenant-a"}),
        permission_codes=frozenset({"post_read"}),
    )


class _PostHistoryConnection:
    """Serve one bounded history query and one batched authorization query."""

    def __init__(self, exchange_count: int, hidden_ids: set[str] | None = None) -> None:
        self.exchange_count = exchange_count
        self.hidden_ids = hidden_ids or set()
        self.calls: list[str] = []

    async def fetch(self, query: str, *args: object):
        self.calls.append(query)
        if "bounded_exchange as materialized" in query:
            return [
                {
                    "exchange_ordinal": index,
                    "question_text": f"Question {index}",
                    "answer_text": f"Answer {index}",
                    "knowledge_cutoff": CUTOFF,
                    "citation_ordinal": 1,
                    "history_citation_ordinal": index,
                    "cited_post_id": str(UUID(int=index)),
                    "post_title": f"Stored title {index}",
                }
                for index in range(1, self.exchange_count + 1)
            ]
        exchange_ordinals, citation_ordinals, citation_ids, _cutoffs, _tenants = args
        return [
            {
                "exchange_ordinal": exchange_ordinal,
                "citation_ordinal": citation_ordinal,
                "post_id": post_id,
                "post_title": f"Authorized title {exchange_ordinal}",
                "project_key": None,
                "project_name": None,
                "truth_status_code": None,
                "truth_order": None,
            }
            for exchange_ordinal, citation_ordinal, post_id in zip(
                exchange_ordinals,
                citation_ordinals,
                citation_ids,
                strict=True,
            )
            if post_id not in self.hidden_ids
        ]


@pytest.mark.parametrize("exchange_count", [1, 10, POST_ASK_HISTORY_EXCHANGE_LIMIT])
def test_stored_post_chat_query_count_is_constant(
    monkeypatch: pytest.MonkeyPatch,
    exchange_count: int,
) -> None:
    async def visible_post(*_args, **_kwargs):
        return {"post_id": "post-1"}

    connection = _PostHistoryConnection(exchange_count)
    monkeypatch.setattr(main, "_load_visible_post", visible_post)

    result = asyncio.run(
        main.read_post_chat(
            post_id="post-1",
            account=_account(),
            pool=_Pool(connection),
        )
    )

    assert len(result["exchanges"]) == exchange_count
    assert len(connection.calls) == 2


def test_stored_post_chat_hides_only_exchange_with_lost_citation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def visible_post(*_args, **_kwargs):
        return {"post_id": "post-1"}

    hidden_id = str(UUID(int=2))
    connection = _PostHistoryConnection(2, {hidden_id})
    monkeypatch.setattr(main, "_load_visible_post", visible_post)

    result = asyncio.run(
        main.read_post_chat(
            post_id="post-1",
            account=_account(),
            pool=_Pool(connection),
        )
    )

    assert [exchange["answer_text"] for exchange in result["exchanges"]] == [
        "Answer 1"
    ]
    assert "Answer 2" not in repr(result)
    assert "Stored title 2" not in repr(result)
    assert hidden_id not in repr(result)


@pytest.mark.parametrize(
    "failure",
    [PostChatHistoryLimitError("too many"), AskEvidenceBatchLimitError("too many")],
)
def test_stored_post_chat_limit_failure_is_actionable(
    monkeypatch: pytest.MonkeyPatch,
    failure: ValueError,
) -> None:
    async def visible_post(*_args, **_kwargs):
        return {"post_id": "post-1"}

    async def stored_chats(*_args, **_kwargs):
        if isinstance(failure, PostChatHistoryLimitError):
            raise failure
        return []

    async def batch_evidence(*_args, **_kwargs):
        raise failure

    monkeypatch.setattr(main, "_load_visible_post", visible_post)
    monkeypatch.setattr(main, "fetch_persisted_chats", stored_chats)
    monkeypatch.setattr(main, "read_authorized_ask_evidence_batch", batch_evidence)

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(
            main.read_post_chat(
                post_id="post-1",
                account=_account(),
                pool=_Pool(object()),
            )
        )
    assert exc_info.value.status_code == 503
    assert "administrator" in str(exc_info.value.detail)


def test_stored_post_chat_omits_an_answer_after_citation_access_is_lost(monkeypatch) -> None:
    async def visible_post(*_args, **_kwargs):
        return {"post_id": "post-1"}

    async def stored_chats(*_args, **_kwargs):
        return [
            {
                "question_text": "What happened?",
                "answer_text": "A formerly authorized answer.",
                "cited_post_ids": ["00000000-0000-4000-8000-000000000099"],
                "cited_posts": [
                    {
                        "post_id": "00000000-0000-4000-8000-000000000099",
                        "post_title": "Hidden",
                    }
                ],
                "_knowledge_cutoff": CUTOFF,
            }
        ]

    async def hidden_evidence(*_args, **_kwargs):
        return (
            AskEvidenceProjection(
                all_citations_visible=False,
                cited_posts=(),
                project_histories=(),
                project_histories_truncated=False,
                knowledge_cutoff="2026-08-20T12:00:00Z",
            ),
        )

    monkeypatch.setattr(main, "_load_visible_post", visible_post)
    monkeypatch.setattr(main, "fetch_persisted_chats", stored_chats)
    monkeypatch.setattr(main, "read_authorized_ask_evidence_batch", hidden_evidence)

    result = asyncio.run(
        main.read_post_chat(
            post_id="post-1",
            account=_account(),
            pool=_Pool(object()),
        )
    )
    assert result == {"post_id": "post-1", "exchanges": []}


def test_global_ask_rejects_stale_session_context_before_reusing_hidden_prose(monkeypatch) -> None:
    async def ensure_session(*_args, **_kwargs):
        return "00000000-0000-4000-8000-000000000010"

    async def unauthorized(*_args, **_kwargs):
        return False

    monkeypatch.setattr(main, "_post_chat_client", lambda: SimpleNamespace(available=True))
    monkeypatch.setattr(main, "ensure_global_ask_session", ensure_session)
    monkeypatch.setattr(main, "global_ask_session_citations_authorized", unauthorized)

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(
            main.ask_agent(
                request=main.GlobalAskRequest(
                    question="Continue the prior answer",
                    session_id="00000000-0000-4000-8000-000000000010",
                ),
                account=_account(),
                pool=_Pool(object()),
                valkey=SimpleNamespace(),
            )
        )

    assert exc_info.value.status_code == 409
    assert "start a new session" in str(exc_info.value.detail).lower()


def test_global_ask_hides_unexpected_provider_errors(monkeypatch) -> None:
    class ProviderFailure:
        available = True

        def answer(self, *args, **kwargs):
            del args, kwargs
            raise RuntimeError("raw provider trace must not reach the buyer")

    async def ensure_session(*_args, **_kwargs):
        return "00000000-0000-4000-8000-000000000010"

    async def authorized(*_args, **_kwargs):
        return True

    async def load_context(*_args, **_kwargs):
        return SimpleNamespace(
            session_id="00000000-0000-4000-8000-000000000010",
            summary="",
            recent_turns=(),
            compress_turns=(),
        )

    async def sources(*_args, **_kwargs):
        return [object()]

    monkeypatch.setattr(main, "_post_chat_client", lambda: ProviderFailure())
    monkeypatch.setattr(main, "ensure_global_ask_session", ensure_session)
    monkeypatch.setattr(main, "global_ask_session_citations_authorized", authorized)
    monkeypatch.setattr(main, "load_global_ask_context", load_context)
    monkeypatch.setattr(main, "gather_global_chat_sources", sources)

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(
            main.ask_agent(
                request=main.GlobalAskRequest(question="What happened?"),
                account=_account(),
                pool=_Pool(object()),
                valkey=SimpleNamespace(),
            )
        )

    assert exc_info.value.status_code == 503
    assert "raw provider trace" not in str(exc_info.value.detail)
