"""Regression tests for the source-grounded Global Ask history queries."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from uuid import UUID

from backend.app.global_ask_history import _visible_post_ids, list_conversations


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


def test_visible_post_ids_uses_fixed_source_and_citation_queries() -> None:
    """Both relation types use fixed identifiers rather than interpolated SQL."""
    for source, table, column in (
        (True, "global_ask_turn_source", "source_post_id"),
        (False, "global_ask_turn_citation", "cited_post_id"),
    ):
        connection = _Connection(
            [
                {
                    "post_id": "post-1",
                    "post_title": "Synthetic source",
                    "visibility_code": "workspace",
                    "corporate_entity_id": "entity-1",
                    "author_account_id": "account-1",
                    "source_detail_state_code": "current",
                }
            ]
        )
        post_ids, rows = asyncio.run(
            _visible_post_ids(
                connection,
                UUID("00000000-0000-0000-0000-000000000004"),
                1,
                lambda row: row["post_id"] == "post-1",
                source=source,
            )
        )

        query, arguments = connection.calls[0]
        assert table in query
        assert column in query
        assert "relation.{" not in query
        assert arguments[1] == 1
        assert post_ids == ["post-1"]
        assert rows["post-1"]["post_title"] == "Synthetic source"
