"""Operator backfill connection recovery contracts."""

from __future__ import annotations

import asyncio
from types import SimpleNamespace

from scripts import backfill_post_content
from lineageweave.post_content_persistence import ImageOcrPreservationError


def test_reconnects_only_after_database_connection_closes(monkeypatch) -> None:
    replacement_connection = object()
    connected_dsns: list[str] = []

    class Connection:
        def __init__(self, closed: bool) -> None:
            self._closed = closed

        def is_closed(self) -> bool:
            return self._closed

    async def connect(dsn: str):
        connected_dsns.append(dsn)
        return replacement_connection

    monkeypatch.setattr(backfill_post_content.asyncpg, "connect", connect)

    current_connection = Connection(False)
    assert (
        asyncio.run(backfill_post_content._ensure_open_connection(current_connection, "dsn"))
        is current_connection
    )
    assert asyncio.run(backfill_post_content._ensure_open_connection(Connection(True), "dsn")) is replacement_connection
    assert connected_dsns == ["dsn"]


def test_backfill_skips_ocr_protected_post_and_continues(monkeypatch) -> None:
    post_ids = [
        "00505695-0000-1fd1-8000-000000000001",
        "00505695-0000-1fd1-8000-000000000002",
    ]

    class Transaction:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, traceback):
            return False

    class Connection:
        def is_closed(self) -> bool:
            return False

        async def fetch(self, query, *args):
            return [{"post_id": post_id} for post_id in post_ids]

        async def fetchrow(self, query, post_id):
            return {
                "post_id": post_id,
                "post_title": "Synthetic title",
                "post_body": "Synthetic body",
                "author_account_id": None,
                "source_process_unit_code": None,
                "source_author_code": None,
                "source_company_code": None,
                "source_customer_code": None,
                "source_project_code": None,
                "source_sales_pool_code": None,
                "corporate_entity_code": None,
            }

        def transaction(self):
            return Transaction()

        async def fetchval(self, query, *args):
            return 0

        async def close(self):
            return None

    connection = Connection()
    persisted: list[str] = []

    async def connect(_dsn):
        return connection

    async def persist(conn, post_id, body, **kwargs):
        persisted.append(post_id)
        if post_id == post_ids[0]:
            raise ImageOcrPreservationError("protected")
        return 1

    async def record_success(conn, post_id, body):
        return None

    class MetadataContext:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, traceback):
            return False

    monkeypatch.setattr(backfill_post_content.asyncpg, "connect", connect)
    monkeypatch.setattr(backfill_post_content, "persist_post_content", persist)
    monkeypatch.setattr(
        backfill_post_content,
        "record_post_content_backfill_success",
        record_success,
    )
    monkeypatch.setattr(
        backfill_post_content,
        "normalize_post_body",
        lambda body, vision_client: SimpleNamespace(image_results=(), text="text"),
    )
    monkeypatch.setattr(
        backfill_post_content,
        "build_post_llm_metadata",
        lambda post_id, row: {},
    )
    monkeypatch.setattr(
        backfill_post_content,
        "use_llm_metadata",
        lambda metadata: MetadataContext(),
    )

    result = asyncio.run(
        backfill_post_content.backfill_post_content(
            "dsn", post_ids, limit=None, normalize_only=True
        )
    )

    assert persisted == post_ids
    assert result["processed_posts"] == 1
    assert result["skipped_posts"] == 1
