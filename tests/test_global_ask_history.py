"""Regression tests for the source-grounded Global Ask history queries."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from uuid import UUID

from backend.app.global_ask_history import _visible_post_ids_batch, list_conversations


class _Connection:
    """Capture bound SQL calls without needing a database for query-shape tests."""

    def __init__(self, rows: list[dict[str, object]]) -> None:
        self.rows = rows
        self.calls: list[tuple[str, tuple[object, ...]]] = []

    async def fetch(self, query: str, *arguments: object) -> list[dict[str, object]]:
        self.calls.append((query, arguments))
        return self.rows


def test_list_conversations_uses_static_sql_and_bound_cursor_values() -> None:
    """Pagination values remain parameters even when a cursor is supplied."""
    connection = _Connection(
        [
            {
                "global_ask_session_id": UUID("00000000-0000-0000-0000-000000000001"),
                "conversation_title": "First",
                "updated_at": datetime(2026, 1, 2, tzinfo=UTC),
                "turn_count": 1,
            },
            {
                "global_ask_session_id": UUID("00000000-0000-0000-0000-000000000002"),
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
            limit=1,
            before_updated_at=cursor_time,
            before_conversation_id=UUID("00000000-0000-0000-0000-000000000003"),
        )
    )

    query, arguments = connection.calls[0]
    assert "{cursor_clause}" not in query
    assert "{limit_placeholder}" not in query
    assert arguments == (
        "account-1",
        cursor_time,
        UUID("00000000-0000-0000-0000-000000000003"),
        2,
    )
    assert len(result["conversations"]) == 1
    assert result["next_cursor"] is not None


def test_list_conversations_first_page_binds_no_null_cursor_parameters() -> None:
    """The no-cursor first page must not send untyped NULL parameters.

    Postgres cannot infer a type for a bare ``$n is null`` parameter, so
    asyncpg's statement Describe fails with AmbiguousParameterError before
    execution — breaking the very first Ask history load for every reader.
    The cursor predicate must therefore be omitted entirely (not NULL-tested)
    when no cursor is supplied.
    """
    connection = _Connection([])

    asyncio.run(list_conversations(connection, "account-1", limit=1))

    query, arguments = connection.calls[0]
    assert "is null" not in query.lower()
    assert arguments == ("account-1", 2)


def test_visible_post_ids_batch_uses_fixed_source_and_citation_queries() -> None:
    """Both relation types use fixed identifiers rather than interpolated SQL."""
    for source, table, column in (
        (True, "global_ask_turn_source", "source_post_id"),
        (False, "global_ask_turn_citation", "cited_post_id"),
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
