from __future__ import annotations

import base64

import pytest

from backend.app.global_ask_media import load_global_ask_content_blocks


ACCOUNT_ID = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
AFFILIATED_ENTITY_ID = "11111111-1111-1111-1111-111111111111"
OTHER_ENTITY_ID = "22222222-2222-2222-2222-222222222222"


class _Connection:
    """Apply a live DB-shaped read and affiliation policy to synthetic rows."""

    def __init__(
        self,
        rows: list[dict[str, object]],
        *,
        affiliations: dict[str, set[str]] | None = None,
        readable_accounts: set[str] | None = None,
    ) -> None:
        self.rows = rows
        self.affiliations = affiliations or {}
        self.readable_accounts = readable_accounts or set()
        self.requested_ids = None
        self.requested_user_account_id = None
        self.media_sql = None

    async def fetch(self, sql: str, post_ids, user_account_id):
        self.requested_ids = post_ids
        self.requested_user_account_id = str(user_account_id)
        self.media_sql = sql
        account_id = str(user_account_id)
        if account_id not in self.readable_accounts:
            return []
        visible_entities = self.affiliations.get(account_id, set())
        requested_ids = {str(post_id) for post_id in post_ids}
        return [
            row
            for row in self.rows
            if str(row["post_id"]) in requested_ids
            and (
                row.get("visibility_code", "public") == "public"
                or row.get("corporate_entity_id") in visible_entities
            )
        ]


@pytest.mark.asyncio
async def test_media_loader_returns_text_and_bounded_cited_raster_images() -> None:
    payload = (
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk"
        "+A8AAQUBAScY42YAAAAASUVORK5CYII="
    )
    svg = base64.b64encode(b"<svg/>").decode("ascii")
    body = f'<img src="data:image/svg+xml;base64,{svg}">'
    body += "".join(f'<img src="data:image/png;base64,{payload}">' for _ in range(5))
    connection = _Connection(
        [
            {
                "post_id": "11111111-1111-1111-1111-111111111111",
                "post_title": "Synthetic source",
                "post_body": body,
            }
        ],
        readable_accounts={ACCOUNT_ID},
    )

    blocks = await load_global_ask_content_blocks(
        connection,
        "The dated source sequence is available.",
        ["11111111-1111-1111-1111-111111111111"],
        ACCOUNT_ID,
    )

    assert len(connection.requested_ids) == 1
    assert connection.requested_user_account_id == ACCOUNT_ID
    assert [block.type for block in blocks] == ["text", "image", "image", "image"]
    assert all(block.mime_type == "image/png" for block in blocks[1:])
    assert base64.b64decode(blocks[1].data_base64 or "") == base64.b64decode(payload)
    # The excluded SVG keeps its DOM position; the first raster is unit one.
    assert blocks[1].unit_index == 1


@pytest.mark.asyncio
async def test_media_loader_rechecks_live_permission_and_affiliation() -> None:
    payload = (
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk"
        "+A8AAQUBAScY42YAAAAASUVORK5CYII="
    )
    body = f'<img src="data:image/png;base64,{payload}">'
    cited_post_ids = [
        "11111111-1111-1111-1111-111111111111",
        "22222222-2222-2222-2222-222222222222",
        "33333333-3333-3333-3333-333333333333",
    ]
    connection = _Connection(
        [
            {
                "post_id": cited_post_ids[0],
                "post_title": "Public source",
                "post_body": body,
                "visibility_code": "public",
                "corporate_entity_id": OTHER_ENTITY_ID,
            },
            {
                "post_id": cited_post_ids[1],
                "post_title": "Private source outside affiliation",
                "post_body": body,
                "visibility_code": "private",
                "corporate_entity_id": OTHER_ENTITY_ID,
            },
            {
                "post_id": cited_post_ids[2],
                "post_title": "Private source in affiliation",
                "post_body": body,
                "visibility_code": "private",
                "corporate_entity_id": AFFILIATED_ENTITY_ID,
            },
        ],
        affiliations={ACCOUNT_ID: {AFFILIATED_ENTITY_ID}},
        readable_accounts={ACCOUNT_ID},
    )

    initially_visible = await load_global_ask_content_blocks(
        connection,
        "Answer",
        cited_post_ids,
        ACCOUNT_ID,
    )
    assert [block.post_id for block in initially_visible[1:]] == [
        cited_post_ids[0],
        cited_post_ids[2],
    ]
    assert "account_affiliation" in (connection.media_sql or "")
    assert "account_role_assignment" in (connection.media_sql or "")
    assert "role_permission" in (connection.media_sql or "")

    # Simulate the affiliation being revoked after source/citation selection.
    connection.affiliations[ACCOUNT_ID].clear()
    after_affiliation_revocation = await load_global_ask_content_blocks(
        connection,
        "Answer",
        cited_post_ids,
        ACCOUNT_ID,
    )
    assert [block.post_id for block in after_affiliation_revocation[1:]] == [cited_post_ids[0]]

    # A live post_read revocation removes even public media from the response.
    connection.readable_accounts.clear()
    after_permission_revocation = await load_global_ask_content_blocks(
        connection,
        "Answer",
        cited_post_ids,
        ACCOUNT_ID,
    )
    assert [block.type for block in after_permission_revocation] == ["text"]


@pytest.mark.asyncio
async def test_media_loader_drops_invalid_citation_ids_without_querying() -> None:
    connection = _Connection([], readable_accounts={ACCOUNT_ID})
    blocks = await load_global_ask_content_blocks(
        connection,
        "Text only",
        ["outside-source"],
        ACCOUNT_ID,
    )
    assert len(blocks) == 1
    assert blocks[0].text == "Text only"
    assert connection.requested_ids is None
