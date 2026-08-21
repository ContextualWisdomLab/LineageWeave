"""Contracts for project histories attached to post-scoped and Global Ask."""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from backend.app import main
from backend.app.ask_project_history import (
    AskEvidenceProjection,
    global_ask_session_citations_authorized,
    read_authorized_ask_evidence,
)
from backend.app.auth import CurrentAccount
from backend.app.post_chat_ingestion import gather_global_chat_sources


CUTOFF = datetime(2026, 8, 20, 12, 0, tzinfo=timezone.utc)


class _EvidenceConnection:
    """Query-shaped double for current citation and project evidence."""

    def __init__(self, rows: list[dict[str, object]]) -> None:
        self.rows = rows
        self.calls: list[tuple[str, tuple[object, ...]]] = []

    async def fetch(self, query: str, *args: object):
        self.calls.append((query, args))
        return self.rows


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
    assert "created_at <= $3" in query
    assert args[2] == CUTOFF


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
    source_queries = [query for query, _args in calls if "array_position($2::uuid[], post_id)" in query]
    assert candidate_queries
    assert all("source_draft_code" in query and "created_at <= $3" in query for query in candidate_queries)
    assert source_queries
    assert "source_deleted_flag" in source_queries[0]
    assert "created_at <= $4" in source_queries[0]


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


def test_stored_post_chat_omits_an_answer_after_citation_access_is_lost(monkeypatch) -> None:
    async def visible_post(*_args, **_kwargs):
        return {"post_id": "post-1"}

    async def stored_chats(*_args, **_kwargs):
        return [
            {
                "question_text": "What happened?",
                "answer_text": "A formerly authorized answer.",
                "cited_post_ids": ["hidden-post"],
                "cited_posts": [{"post_id": "hidden-post", "post_title": "Hidden"}],
                "_knowledge_cutoff": CUTOFF,
            }
        ]

    async def hidden_evidence(*_args, **_kwargs):
        return AskEvidenceProjection(
            all_citations_visible=False,
            cited_posts=(),
            project_histories=(),
            project_histories_truncated=False,
            knowledge_cutoff="2026-08-20T12:00:00Z",
        )

    monkeypatch.setattr(main, "_load_visible_post", visible_post)
    monkeypatch.setattr(main, "fetch_persisted_chats", stored_chats)
    monkeypatch.setattr(main, "read_authorized_ask_evidence", hidden_evidence)

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
