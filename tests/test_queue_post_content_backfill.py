"""Operator safeguards for explicit post-content retries."""

from __future__ import annotations

from contextlib import asynccontextmanager
from types import SimpleNamespace
from uuid import UUID

import pytest

from scripts import queue_post_content_backfill


class _Connection:
    def __init__(self, rows):
        self.rows = rows

    async def fetch(self, _query, _post_ids):
        return self.rows

    @asynccontextmanager
    async def transaction(self):
        yield self


class _Client:
    pass


def test_normalize_retry_post_ids_deduplicates_and_rejects_invalid_values() -> None:
    post_id = "00505695-3e61-1fd1-83c5-263f88a9e77a"
    assert queue_post_content_backfill._normalize_retry_post_ids([post_id, post_id]) == (
        UUID(post_id),
    )
    with pytest.raises(ValueError, match="invalid --retry-post-id"):
        queue_post_content_backfill._normalize_retry_post_ids(["not-a-uuid"])


def test_explicit_retry_requeues_only_selected_rows(monkeypatch) -> None:
    post_id = "00505695-3e61-1fd1-83c5-263f88a9e77a"
    connection = _Connection([{"post_id": post_id, "post_body": "body"}])
    calls: list[str] = []

    async def requeue(_connection, selected_id, body):
        calls.append(f"{selected_id}:{body}")
        return SimpleNamespace(source_body_sha256="a" * 64)

    async def publish(_client, *, post_id: str, source_body_digest: str):
        assert post_id == "00505695-3e61-1fd1-83c5-263f88a9e77a"
        assert source_body_digest == "a" * 64
        return "1-0"

    monkeypatch.setattr(queue_post_content_backfill, "requeue_failed_post_content_job", requeue)
    monkeypatch.setattr(queue_post_content_backfill, "publish_post_content_event", publish)

    result = __import__("asyncio").run(
        queue_post_content_backfill._retry_explicit_post_content_jobs(
            connection,
            _Client(),
            [post_id, post_id],
        )
    )

    assert result == {"retried_posts": 1, "retry_published_events": 1}
    assert calls == [f"{post_id}:body"]
