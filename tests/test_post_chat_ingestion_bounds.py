from __future__ import annotations

from types import SimpleNamespace

import pytest

from backend.app import post_chat_ingestion


class _Connection:
    """Return one anchor and a deliberately oversized linked candidate set."""

    async def fetchrow(self, _sql: str, _post_id: str):
        return {
            "post_id": "anchor",
            "post_title": "Anchor",
            "post_body": "anchor body",
            "created_at": None,
        }

    async def fetch(self, _sql: str, _post_ids):
        ids = ["private-other", "direct-b", "indirect-c", "direct-a"] + [
            f"indirect-{index}" for index in range(10)
        ]
        return [
            {
                "post_id": post_id,
                "post_title": post_id,
                "post_body": post_id,
                "visibility_code": "private" if post_id == "private-other" else "public",
                "corporate_entity_id": "other-entity",
                "created_at": None,
            }
            for post_id in ids
        ]


@pytest.mark.asyncio
async def test_gather_chat_sources_bounds_normalization_and_prioritizes_direct_links(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    normalized: list[str] = []

    def fake_normalize(body: str, **_kwargs):
        normalized.append(body)
        return SimpleNamespace(text=body)

    async def fake_find(_conn, _post_id):
        return post_chat_ingestion.LinkedPostIds(
            direct=frozenset({"direct-a", "direct-b"}),
            indirect=frozenset({"private-other", "indirect-c", *{f"indirect-{i}" for i in range(10)}}),
        )

    monkeypatch.setattr(post_chat_ingestion, "normalize_post_body", fake_normalize)
    monkeypatch.setattr(post_chat_ingestion, "find_linked_post_ids", fake_find)

    sources = await post_chat_ingestion.gather_chat_sources(
        _Connection(),
        "anchor",
        lambda row: row["visibility_code"] == "public",
    )

    assert [source.post_id for source in sources] == [
        "anchor",
        "direct-a",
        "direct-b",
        "indirect-0",
        "indirect-1",
        "indirect-2",
    ]
    assert normalized == [
        "anchor body",
        "direct-a",
        "direct-b",
        "indirect-0",
        "indirect-1",
        "indirect-2",
    ]
    assert "private-other" not in normalized
