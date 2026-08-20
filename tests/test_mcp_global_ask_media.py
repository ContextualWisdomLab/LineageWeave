from __future__ import annotations

import base64

import pytest

from backend.app.global_ask_media import load_global_ask_content_blocks


class _Connection:
    """Return only the cited synthetic source row and record requested ids."""

    def __init__(self, rows: list[dict[str, object]]) -> None:
        self.rows = rows
        self.requested_ids = None

    async def fetch(self, _sql: str, post_ids):
        self.requested_ids = post_ids
        return self.rows


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
        ]
    )

    blocks = await load_global_ask_content_blocks(
        connection,
        "The dated source sequence is available.",
        ["11111111-1111-1111-1111-111111111111"],
    )

    assert len(connection.requested_ids) == 1
    assert [block.type for block in blocks] == ["text", "image", "image", "image"]
    assert all(block.mime_type == "image/png" for block in blocks[1:])
    assert base64.b64decode(blocks[1].data_base64 or "") == base64.b64decode(payload)
    assert blocks[1].unit_index == 0


@pytest.mark.asyncio
async def test_media_loader_drops_invalid_citation_ids_without_querying() -> None:
    connection = _Connection([])
    blocks = await load_global_ask_content_blocks(connection, "Text only", ["outside-source"])
    assert len(blocks) == 1
    assert blocks[0].text == "Text only"
    assert connection.requested_ids is None
