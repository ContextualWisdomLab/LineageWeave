"""Unit tests for the authorized post-filter projection."""

from __future__ import annotations

import asyncio
from typing import Any

from backend.app.main import _post_filter_options


class _RecordingConnection:
    """Return synthetic option rows while recording database round trips."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, tuple[Any, ...]]] = []

    async def fetch(self, query: str, *args: Any) -> list[dict[str, object]]:
        """Record the closed query and return both supported option categories."""
        self.calls.append((query, args))
        return [
            {
                "lookup_category": "post_visibility",
                "code": "public",
                "label": "Public",
                "display_order": 1,
            },
            {
                "lookup_category": "post_visibility",
                "code": "private",
                "label": "Private",
                "display_order": 2,
            },
            {
                "lookup_category": "voc_type",
                "code": "voc",
                "label": "Voice of Customer",
                "display_order": 1,
            },
        ]


def test_post_filter_options_use_one_authorized_source_scan() -> None:
    """Both complete option lists share one parameterized ABAC-filtered query."""
    conn = _RecordingConnection()

    voc_types, visibilities = asyncio.run(
        _post_filter_options(conn, frozenset({"corp-a"}), frozenset({"pu-a"}))
    )

    assert voc_types == [{"code": "voc", "label": "Voice of Customer"}]
    assert visibilities == [
        {"code": "public", "label": "Public"},
        {"code": "private", "label": "Private"},
    ]
    assert len(conn.calls) == 1
    query, args = conn.calls[0]
    assert "cross join lateral" in query
    assert "('post_visibility', post.visibility_code)" in query
    assert "('voc_type', post.voc_type_code)" in query
    assert "post.corporate_entity_id::text = any($1::text[])" in query
    assert "post.process_unit_id::text = any($2::text[])" in query
    assert "nullif(btrim(post.source_draft_code), '') is null" in query
    assert "nullif(btrim(post.source_deleted_flag), '') is null" in query
    assert args == (["corp-a"], ["pu-a"])
