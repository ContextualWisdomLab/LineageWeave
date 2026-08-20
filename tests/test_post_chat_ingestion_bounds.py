from __future__ import annotations

from types import SimpleNamespace

import pytest

from backend.app import post_chat_ingestion


VISIBLE_ENTITY_ID = "11111111-1111-1111-1111-111111111111"
OTHER_ENTITY_ID = "22222222-2222-2222-2222-222222222222"


class _Connection:
    """Record the metadata-first and authorized-body-only read sequence."""

    def __init__(
        self,
        *,
        anchor_visibility: str = "public",
        anchor_entity_id: str = OTHER_ENTITY_ID,
    ) -> None:
        self.anchor_visibility = anchor_visibility
        self.anchor_entity_id = anchor_entity_id
        self.anchor_metadata_sql = ""
        self.anchor_body_sql = ""
        self.linked_metadata_sql = ""
        self.linked_body_sql = ""
        self.anchor_body_loaded = False
        self.linked_body_ids: tuple[str, ...] = ()

    async def fetchrow(self, sql: str, _post_id: str):
        self.anchor_metadata_sql = sql
        assert "post_body" not in sql
        return {
            "post_id": "anchor",
            "post_title": "Anchor",
            "visibility_code": self.anchor_visibility,
            "corporate_entity_id": self.anchor_entity_id,
            "created_at": None,
        }

    async def fetchval(self, sql: str, _post_id: str):
        self.anchor_body_sql = sql
        self.anchor_body_loaded = True
        return "anchor body"

    async def fetch(self, sql: str, post_ids):
        if " as fact" in sql or "knowledge_graph_edge" in sql:
            return []
        if "post_body" in sql:
            self.linked_body_sql = sql
            self.linked_body_ids = tuple(str(post_id) for post_id in post_ids)
            return [
                {"post_id": post_id, "post_body": str(post_id)}
                for post_id in post_ids
            ]

        self.linked_metadata_sql = sql
        assert "post_body" not in sql
        ids = [
            "aaa-private-other",
            "aaa-private-visible",
            "direct-b",
            "indirect-c",
            "direct-a",
            *[f"indirect-{index}" for index in range(10)],
        ]
        return [
            {
                "post_id": post_id,
                "post_title": post_id,
                "visibility_code": (
                    "private"
                    if post_id in {"aaa-private-other", "aaa-private-visible"}
                    else "public"
                ),
                "corporate_entity_id": (
                    VISIBLE_ENTITY_ID
                    if post_id == "aaa-private-visible"
                    else OTHER_ENTITY_ID
                ),
                "created_at": None,
            }
            for post_id in ids
        ]


@pytest.mark.asyncio
async def test_gather_chat_sources_bounds_normalization_and_prioritizes_direct_links(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Only bounded, ABAC-admitted rows have their bodies loaded or normalized."""
    normalized: list[str] = []

    def fake_normalize(body: str, **_kwargs):
        normalized.append(body)
        return SimpleNamespace(text=body)

    async def fake_find(_conn, _post_id):
        return post_chat_ingestion.LinkedPostIds(
            direct=frozenset({"direct-a", "direct-b"}),
            indirect=frozenset(
                {
                    "aaa-private-other",
                    "aaa-private-visible",
                    "indirect-c",
                    *{f"indirect-{index}" for index in range(10)},
                }
            ),
        )

    monkeypatch.setattr(post_chat_ingestion, "normalize_post_body", fake_normalize)
    monkeypatch.setattr(post_chat_ingestion, "find_linked_post_ids", fake_find)
    connection = _Connection()

    sources = await post_chat_ingestion.gather_chat_sources(
        connection,
        "anchor",
        lambda row: (
            row["visibility_code"] == "public"
            or row["corporate_entity_id"] == VISIBLE_ENTITY_ID
        ),
    )

    assert [source.post_id for source in sources] == [
        "anchor",
        "direct-a",
        "direct-b",
        "aaa-private-visible",
        "indirect-0",
        "indirect-1",
    ]
    assert normalized == [
        "anchor body",
        "direct-a",
        "direct-b",
        "aaa-private-visible",
        "indirect-0",
        "indirect-1",
    ]
    assert connection.anchor_body_loaded is True
    assert "post_body" not in connection.anchor_metadata_sql
    assert "post_body" in connection.anchor_body_sql
    assert "post_body" not in connection.linked_metadata_sql
    assert "post_body" in connection.linked_body_sql
    assert connection.linked_body_ids == (
        "direct-a",
        "direct-b",
        "aaa-private-visible",
        "indirect-0",
        "indirect-1",
    )
    assert "aaa-private-other" not in connection.linked_body_ids
    assert "indirect-2" not in connection.linked_body_ids


@pytest.mark.asyncio
async def test_gather_chat_sources_never_loads_an_unauthorized_private_anchor(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A hidden anchor is rejected before its body enters application memory."""
    normalized: list[str] = []

    def fake_normalize(body: str, **_kwargs):
        normalized.append(body)
        return SimpleNamespace(text=body)

    monkeypatch.setattr(post_chat_ingestion, "normalize_post_body", fake_normalize)
    connection = _Connection(anchor_visibility="private", anchor_entity_id=OTHER_ENTITY_ID)

    sources = await post_chat_ingestion.gather_chat_sources(
        connection,
        "anchor",
        lambda _row: False,
    )

    assert sources == []
    assert normalized == []
    assert connection.anchor_body_loaded is False
    assert connection.anchor_body_sql == ""
    assert connection.linked_metadata_sql == ""
    assert connection.linked_body_sql == ""
