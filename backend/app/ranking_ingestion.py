"""Load ABAC-visible posts for the RankWeave ranking port.

A hidden post is omitted from every channel. This module never invents
a fused score or a theta.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Callable, Mapping

if TYPE_CHECKING:
    import asyncpg

__all__ = ["load_visible_ranking_posts"]


async def load_visible_ranking_posts(
    conn: "asyncpg.Connection",
    can_see_post: Callable[[Mapping[str, Any]], bool],
) -> list[dict[str, Any]]:
    """Read ``source_post`` rows the buyer may rank."""
    posts = await conn.fetch(
        "select post_id, post_title, created_at, visibility_code, "
        "corporate_entity_id, process_unit_id from source_post"
    )
    return [dict(row) for row in posts if can_see_post(row)]
