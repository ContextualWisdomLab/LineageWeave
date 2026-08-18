from __future__ import annotations

import asyncio

from backend.app.post_chat_ingestion import gather_global_chat_sources


def test_global_sources_apply_visibility_before_normalization() -> None:
    rows = [
        {
            "post_id": "public-post",
            "post_title": "Public evidence",
            "post_body": "<p>public body</p>",
            "visibility_code": "public",
            "corporate_entity_id": None,
        },
        {
            "post_id": "private-affiliated",
            "post_title": "Affiliated evidence",
            "post_body": "<p>affiliated body</p>",
            "visibility_code": "private",
            "corporate_entity_id": "corp-demo",
        },
        {
            "post_id": "private-hidden",
            "post_title": "Hidden evidence",
            "post_body": "<p>hidden body</p>",
            "visibility_code": "private",
            "corporate_entity_id": "corp-other",
        },
    ]

    class FakeConnection:
        async def fetch(self, query: str, *args):
            return rows if "from source_post" in query else []

    sources = asyncio.run(
        gather_global_chat_sources(
            FakeConnection(),
            lambda row: row["visibility_code"] == "public"
            or row["corporate_entity_id"] == "corp-demo",
        )
    )

    assert [source.post_id for source in sources] == ["public-post", "private-affiliated"]
    assert sources[0].post_body == "public body"
    assert sources[1].post_body == "affiliated body"
