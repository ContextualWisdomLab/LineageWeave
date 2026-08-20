from __future__ import annotations

from types import SimpleNamespace

import pytest

from backend.app import post_chat_ingestion


VISIBLE_ENTITY_ID = "11111111-1111-1111-1111-111111111111"
OTHER_ENTITY_ID = "22222222-2222-2222-2222-222222222222"


class _Connection:
    """Apply a DB-shaped visibility predicate before returning source bodies."""

    def __init__(
        self,
        *,
        anchor_visibility: str = "public",
        anchor_entity_id: str = OTHER_ENTITY_ID,
    ) -> None:
        self.anchor_visibility = anchor_visibility
        self.anchor_entity_id = anchor_entity_id
        self.anchor_sql = ""
        self.linked_sql = ""
        self.visibility_scopes: list[tuple[str, ...]] = []

    async def fetchrow(self, sql: str, _post_id: str, visible_entity_ids):
        self.anchor_sql = sql
        scope = tuple(str(value) for value in visible_entity_ids)
        self.visibility_scopes.append(scope)
        if self.anchor_visibility != "public" and self.anchor_entity_id not in scope:
            return None
        return {
            "post_id": "anchor",
            "post_title": "Anchor",
            "post_body": "anchor body",
            "visibility_code": self.anchor_visibility,
            "corporate_entity_id": self.anchor_entity_id,
            "created_at": None,
        }

    async def fetch(self, sql: str, _post_ids, visible_entity_ids):
        self.linked_sql = sql
        scope = tuple(str(value) for value in visible_entity_ids)
        self.visibility_scopes.append(scope)
        ids = [
            "private-other",
            "private-visible",
            "direct-b",
            "indirect-c",
            "direct-a",
            *[f"indirect-{index}" for index in range(10)],
        ]
        rows = [
            {
                "post_id": post_id,
                "post_title": post_id,
                "post_body": post_id,
                "visibility_code": (
                    "private" if post_id in {"private-other", "private-visible"} else "public"
                ),
                "corporate_entity_id": (
                    VISIBLE_ENTITY_ID if post_id == "private-visible" else OTHER_ENTITY_ID
                ),
                "created_at": None,
            }
            for post_id in ids
        ]
        return [
            row
            for row in rows
            if row["visibility_code"] == "public" or row["corporate_entity_id"] in scope
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
            indirect=frozenset(
                {
                    "private-other",
                    "private-visible",
                    "indirect-c",
                    *{f"indirect-{i}" for i in range(10)},
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
        visible_corporate_entity_ids=(VISIBLE_ENTITY_ID,),
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
    assert "visibility_code = 'public'" in connection.anchor_sql
    assert "visibility_code = 'public'" in connection.linked_sql
    assert "corporate_entity_id = any($2::uuid[])" in connection.anchor_sql
    assert "corporate_entity_id = any($2::uuid[])" in connection.linked_sql
    assert connection.visibility_scopes == [(VISIBLE_ENTITY_ID,), (VISIBLE_ENTITY_ID,)]


@pytest.mark.asyncio
async def test_gather_chat_sources_never_loads_an_unauthorized_private_anchor(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A private anchor outside the SQL visibility scope never reaches normalization."""
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
        visible_corporate_entity_ids=(VISIBLE_ENTITY_ID,),
    )

    assert sources == []
    assert normalized == []
    assert connection.linked_sql == ""
    assert connection.visibility_scopes == [(VISIBLE_ENTITY_ID,)]
