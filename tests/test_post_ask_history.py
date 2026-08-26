"""Regression tests for account-owned per-post Ask history queries."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from uuid import UUID

import pytest
from fastapi import HTTPException

from backend.app.auth import CurrentAccount
from backend.app import main as post_ask_main
from backend.app.post_ask_history import (
    PostAskConversationNotFound,
    PostAskEvidenceChanged,
    _visible_post_ids_batch,
    conversation_exists,
    list_conversations,
    persist_turn,
)


class _Connection:
    """Capture bound SQL calls without needing a database for query-shape tests."""

    def __init__(self, rows: list[dict[str, object]] | None = None) -> None:
        self.rows = rows or []
        self.calls: list[tuple[str, tuple[object, ...]]] = []

    async def fetch(self, query: str, *arguments: object) -> list[dict[str, object]]:
        self.calls.append((query, arguments))
        return self.rows

    async def fetchval(self, query: str, *arguments: object) -> object:
        self.calls.append((query, arguments))
        if "exists(" in query:
            return True
        if "coalesce(max(turn_ordinal)" in query:
            return 1
        return None

    async def fetchrow(self, query: str, *arguments: object) -> dict[str, object] | None:
        self.calls.append((query, arguments))
        return {"post_ask_session_id": arguments[0]}

    async def execute(self, query: str, *arguments: object) -> str:
        self.calls.append((query, arguments))
        return "INSERT 0 1"

    def transaction(self) -> _Connection:
        return self

    async def __aenter__(self) -> _Connection:
        return self

    async def __aexit__(self, *_exc: object) -> None:
        return None


def test_list_conversations_binds_account_post_and_cursor() -> None:
    """Pagination and post scope remain parameters, never interpolated SQL."""
    connection = _Connection(
        [
            {
                "post_ask_session_id": UUID("00000000-0000-0000-0000-000000000001"),
                "conversation_title": "First",
                "updated_at": datetime(2026, 1, 2, tzinfo=UTC),
                "turn_count": 1,
            },
            {
                "post_ask_session_id": UUID("00000000-0000-0000-0000-000000000002"),
                "conversation_title": "Second",
                "updated_at": datetime(2026, 1, 1, tzinfo=UTC),
                "turn_count": 2,
            },
        ]
    )
    cursor_time = datetime(2026, 1, 3, tzinfo=UTC)

    result = asyncio.run(
        list_conversations(
            connection,
            "account-1",
            "post-1",
            limit=1,
            before_updated_at=cursor_time,
            before_conversation_id=UUID("00000000-0000-0000-0000-000000000003"),
        )
    )

    query, arguments = connection.calls[0]
    assert "{cursor_clause}" not in query
    assert "post_ask_session" in query
    assert arguments == (
        "account-1",
        "post-1",
        cursor_time,
        UUID("00000000-0000-0000-0000-000000000003"),
        2,
    )
    assert len(result["conversations"]) == 1
    assert result["next_cursor"] is not None
    assert result["conversations"][0]["conversation_id"] == "00000000-0000-0000-0000-000000000001"


def test_conversation_exists_requires_account_and_post() -> None:
    """A conversation id from another post or account must not match."""
    connection = _Connection()
    conversation_id = UUID("00000000-0000-0000-0000-000000000009")

    found = asyncio.run(
        conversation_exists(connection, "account-1", "post-1", conversation_id)
    )

    query, arguments = connection.calls[0]
    assert "post_ask_session" in query
    assert arguments == (conversation_id, "account-1", "post-1")
    assert found is True


def test_visible_post_ids_batch_uses_fixed_source_and_citation_queries() -> None:
    """Both relation types use fixed identifiers rather than interpolated SQL."""
    for source, table, column in (
        (True, "post_ask_turn_source", "source_post_id"),
        (False, "post_ask_turn_citation", "cited_post_id"),
    ):
        connection = _Connection(
            [
                {
                    "turn_ordinal": 1,
                    "post_id": "post-1",
                    "post_title": "Synthetic source",
                    "visibility_code": "workspace",
                    "corporate_entity_id": "entity-1",
                    "author_account_id": "account-1",
                    "source_detail_state_code": "current",
                }
            ]
        )
        by_turn = asyncio.run(
            _visible_post_ids_batch(
                connection,
                UUID("00000000-0000-0000-0000-000000000004"),
                [1],
                lambda row: row["post_id"] == "post-1",
                source=source,
            )
        )
        post_ids, rows = by_turn[1]

        query, arguments = connection.calls[0]
        assert table in query
        assert column in query
        assert "relation.{" not in query
        assert "source_draft_code" in query
        assert "source_deleted_flag" in query
        assert "post.process_unit_id" in query
        assert arguments[1] == [1]
        assert post_ids == ["post-1"]
        assert rows["post-1"]["post_title"] == "Synthetic source"


def test_visible_post_ids_batch_stays_at_one_query_regardless_of_turn_count() -> None:
    """Query count must not grow with the number of turns being reauthorized."""
    connection = _Connection([])

    by_turn = asyncio.run(
        _visible_post_ids_batch(
            connection,
            UUID("00000000-0000-0000-0000-000000000004"),
            list(range(1, 51)),
            lambda row: True,
            source=True,
        )
    )

    assert len(connection.calls) == 1
    assert set(by_turn.keys()) == set(range(1, 51))
    assert all(ids == [] and rows == {} for ids, rows in by_turn.values())


def test_visible_post_ids_batch_never_leaks_a_row_into_the_wrong_turn() -> None:
    """A row is partitioned to its own turn_ordinal, never a neighboring turn."""
    connection = _Connection(
        [
            {
                "turn_ordinal": 1,
                "post_id": "post-turn-1",
                "post_title": "Turn 1 post",
                "visibility_code": "public",
                "corporate_entity_id": "entity-1",
                "author_account_id": "account-1",
                "source_detail_state_code": "current",
            },
            {
                "turn_ordinal": 2,
                "post_id": "post-turn-2",
                "post_title": "Turn 2 post",
                "visibility_code": "public",
                "corporate_entity_id": "entity-1",
                "author_account_id": "account-1",
                "source_detail_state_code": "current",
            },
        ]
    )

    by_turn = asyncio.run(
        _visible_post_ids_batch(
            connection,
            UUID("00000000-0000-0000-0000-000000000004"),
            [1, 2, 3],
            lambda row: True,
            source=False,
        )
    )

    assert by_turn[1][0] == ["post-turn-1"]
    assert by_turn[2][0] == ["post-turn-2"]
    assert by_turn[3] == ([], {})


def test_persist_turn_creates_a_new_session_then_writes_the_turn() -> None:
    """A completed answer is stored under the calling account and post."""
    connection = _Connection()
    conversation_id = asyncio.run(
        persist_turn(
            connection,
            "account-1",
            "post-1",
            None,
            "Which site visit was saved?",
            "The saved post answer stays grounded in the linked source.",
            ["post-1", "post-2"],
            ["post-2"],
        )
    )

    statements = [query for query, _arguments in connection.calls]
    assert any("insert into post_ask_session" in query for query in statements)
    assert any("insert into post_ask_turn" in query for query in statements)
    assert any("insert into post_ask_turn_source" in query for query in statements)
    assert any("insert into post_ask_turn_citation" in query for query in statements)
    session_arguments = next(
        arguments
        for query, arguments in connection.calls
        if "insert into post_ask_session" in query
    )
    assert session_arguments[0] == conversation_id
    assert session_arguments[1:] == ("post-1", "account-1")


def test_persist_turn_rejects_a_conversation_outside_the_account_post_scope() -> None:
    """An existing conversation must belong to both the caller and post."""

    class _MissingConversationConnection(_Connection):
        async def fetchrow(self, query: str, *arguments: object) -> None:
            self.calls.append((query, arguments))
            return None

    connection = _MissingConversationConnection()

    with pytest.raises(PostAskConversationNotFound):
        asyncio.run(
            persist_turn(
                connection,
                "account-1",
                "post-1",
                UUID("00000000-0000-0000-0000-000000000005"),
                "What changed?",
                "An answer.",
                ["post-1"],
                [],
            )
        )

    assert not any("insert into post_ask_turn" in query for query, _ in connection.calls)


def test_persist_turn_locks_existing_session_before_allocating_ordinal() -> None:
    """Every existing-session append is serialized before choosing its ordinal."""
    connection = _Connection()

    asyncio.run(
        persist_turn(
            connection,
            "account-1",
            "post-1",
            UUID("00000000-0000-0000-0000-000000000005"),
            "What changed?",
            "An answer.",
            ["post-1"],
            [],
        )
    )

    statements = [query for query, _arguments in connection.calls]
    lock_index = next(
        index for index, query in enumerate(statements)
        if "from post_ask_session" in query and "for update" in query
    )
    ordinal_index = next(
        index for index, query in enumerate(statements)
        if "coalesce(max(turn_ordinal)" in query
    )
    assert lock_index < ordinal_index


def test_persist_post_ask_turn_starts_a_new_conversation_if_a_confirmed_one_is_deleted(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A deletion after answer work preserves the answer without bypassing the write boundary."""
    deleted_conversation_id = UUID("00000000-0000-0000-0000-000000000006")
    replacement_conversation_id = UUID("00000000-0000-0000-0000-000000000007")
    calls: list[UUID | None] = []

    async def persist(
        _conn: object,
        _user_account_id: str,
        _post_id: str,
        conversation_id: UUID | None,
        *_args: object,
        **_kwargs: object,
    ) -> UUID:
        calls.append(conversation_id)
        if conversation_id == deleted_conversation_id:
            raise PostAskConversationNotFound
        return replacement_conversation_id

    monkeypatch.setattr(post_ask_main, "persist_post_ask_turn", persist)
    account = CurrentAccount(
        user_account_id="account-1",
        external_subject_id="subject-1",
        display_name="Synthetic analyst",
        preferred_locale="en",
        corporate_entity_ids=frozenset(),
        process_unit_ids=frozenset(),
        permission_codes=frozenset({"post_read"}),
    )

    conversation_id = asyncio.run(
        post_ask_main._persist_post_ask_turn(
            _Connection(),
            account,
            "post-1",
            deleted_conversation_id,
            "What changed?",
            "The completed answer remains available.",
            ["post-1"],
            [],
            recover_deleted_conversation=True,
        )
    )

    assert conversation_id == replacement_conversation_id
    assert calls == [deleted_conversation_id, None]


def test_deleted_conversation_recovery_maps_changed_evidence_to_retry_guidance(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Recovery must preserve the normal evidence-change HTTP boundary."""
    deleted_conversation_id = UUID("00000000-0000-0000-0000-000000000008")

    async def persist(
        _conn: object,
        _user_account_id: str,
        _post_id: str,
        conversation_id: UUID | None,
        *_args: object,
        **_kwargs: object,
    ) -> UUID:
        if conversation_id == deleted_conversation_id:
            raise PostAskConversationNotFound
        raise PostAskEvidenceChanged

    monkeypatch.setattr(post_ask_main, "persist_post_ask_turn", persist)
    account = CurrentAccount(
        user_account_id="account-1",
        external_subject_id="subject-1",
        display_name="Synthetic analyst",
        preferred_locale="en",
        corporate_entity_ids=frozenset(),
        process_unit_ids=frozenset(),
        permission_codes=frozenset({"post_read"}),
    )

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(
            post_ask_main._persist_post_ask_turn(
                _Connection(),
                account,
                "post-1",
                deleted_conversation_id,
                "What changed?",
                "The completed answer remains available.",
                ["post-1"],
                [],
                recover_deleted_conversation=True,
            )
        )

    assert exc_info.value.status_code == 503


def test_persist_turn_aborts_when_a_citation_loses_authorization() -> None:
    """The transaction fails closed if cited evidence is no longer visible."""
    connection = _Connection([
        {
            "post_id": "post-2",
            "post_title": "Synthetic source",
            "visibility_code": "workspace",
            "corporate_entity_id": "entity-2",
            "author_account_id": "account-2",
            "source_detail_state_code": "current",
        }
    ])

    with pytest.raises(PostAskEvidenceChanged):
        asyncio.run(
            persist_turn(
                connection,
                "account-1",
                "post-1",
                None,
                "What changed?",
                "A complete answer.",
                ["post-1", "post-2"],
                ["post-2"],
                can_see_post=lambda _row: False,
            )
        )

    assert any("for share of post" in query.lower() for query, _ in connection.calls)
    assert any(
        "post.process_unit_id" in query and "for share of post" in query.lower()
        for query, _ in connection.calls
    )


def test_persist_turn_aborts_when_a_non_cited_source_loses_authorization() -> None:
    """Every gathered source is reauthorized even when it is not cited."""
    connection = _Connection([
        {
            "post_id": "post-1",
            "post_title": "Synthetic context",
            "visibility_code": "workspace",
            "corporate_entity_id": "entity-1",
            "author_account_id": "account-1",
            "source_detail_state_code": "current",
        },
        {
            "post_id": "post-2",
            "post_title": "Synthetic citation",
            "visibility_code": "workspace",
            "corporate_entity_id": "entity-2",
            "author_account_id": "account-2",
            "source_detail_state_code": "current",
        },
    ])

    with pytest.raises(PostAskEvidenceChanged):
        asyncio.run(
            persist_turn(
                connection,
                "account-1",
                "post-1",
                None,
                "What changed?",
                "A complete answer.",
                ["post-1", "post-2"],
                ["post-2"],
                can_see_post=lambda row: row["post_id"] == "post-2",
            )
        )

    assert not any("insert into post_ask_turn" in query for query, _ in connection.calls)


def test_persist_turn_rejects_deleted_source_before_foreign_key_insert() -> None:
    """A source deleted mid-request becomes evidence-changed, never a raw FK error."""
    connection = _Connection([])

    with pytest.raises(PostAskEvidenceChanged):
        asyncio.run(
            persist_turn(
                connection,
                "account-1",
                "post-1",
                None,
                "What changed?",
                "A complete answer.",
                ["post-1", "post-2"],
                ["post-2"],
                can_see_post=lambda _row: True,
            )
        )

    assert not any(
        "insert into post_ask_turn_source" in query
        or "insert into post_ask_turn_citation" in query
        for query, _ in connection.calls
    )
