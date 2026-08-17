"""Load visible posts + visible-only lineage edges as ThreadWeave messages.

A hidden parent is omitted from ``references`` so the visible child
becomes a JWZ root. This module never invents a parent id.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Callable, Mapping

from lineageweave.threadweave_client import conversation_messages_from_rows

if TYPE_CHECKING:
    import asyncpg

__all__ = [
    "conversation_messages_from_rows",
    "load_visible_conversation_messages",
]


async def load_visible_conversation_messages(
    conn: "asyncpg.Connection",
    can_see_post: Callable[[Mapping[str, Any]], bool],
) -> list[dict[str, Any]]:
    """Read ``source_post`` / ``post_lineage_edge`` and drop hidden parents."""
    posts = await conn.fetch(
        "select post_id, post_title, visibility_code, corporate_entity_id "
        "from source_post"
    )
    edges = await conn.fetch(
        "select parent_post_id, child_post_id from post_lineage_edge"
    )
    return conversation_messages_from_rows(posts, edges, can_see_post)
