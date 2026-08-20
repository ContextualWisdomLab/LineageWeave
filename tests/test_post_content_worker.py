"""Worker regression tests for durable post-content completeness."""

from __future__ import annotations

import asyncio
from typing import Any

from backend.app import post_content_worker
from backend.app.post_content_queue import POST_CONTENT_STREAM_KEY, SUCCEEDED


class _Transaction:
    async def __aenter__(self) -> "_Transaction":
        return self

    async def __aexit__(self, *_exc: Any) -> None:
        return None


class _Acquire:
    def __init__(self, connection: "_Connection") -> None:
        self.connection = connection

    async def __aenter__(self) -> "_Connection":
        return self.connection

    async def __aexit__(self, *_exc: Any) -> None:
        return None


class _Connection:
    def __init__(self) -> None:
        self.executed: list[str] = []

    def transaction(self) -> _Transaction:
        return _Transaction()

    async def fetchrow(self, *_args: Any) -> dict[str, Any]:
        return {
            "post_id": "00000000-0000-0000-0000-000000000001",
            "post_body": "body",
            "post_title": "title",
            "job_status_code": SUCCEEDED,
            "job_started_at": None,
        }

    async def fetchval(self, query: str, *_args: Any) -> int:
        assert "coalesce(max(status_ordinal)" in query
        return 0

    async def execute(self, query: str, *_args: Any) -> None:
        self.executed.append(query)


class _Pool:
    def __init__(self) -> None:
        self.connection = _Connection()

    def acquire(self) -> _Acquire:
        return _Acquire(self.connection)


def test_worker_starts_after_historical_stream_tail() -> None:
    class Client:
        async def xrevrange(self, key: str, *, count: int):
            assert key == POST_CONTENT_STREAM_KEY
            assert count == 1
            return [("123-0", {})]

    assert asyncio.run(post_content_worker._stream_tail(Client())) == "123-0"


def test_worker_reclaims_successful_job_when_embeddings_are_incomplete(monkeypatch) -> None:
    pool = _Pool()
    calls: list[str] = []

    async def incomplete(
        _connection, post_id: str, *, embedding_model_code: str, require_structure: bool
    ) -> bool:
        calls.append(f"{post_id}:{embedding_model_code}")
        assert require_structure is True
        return False

    monkeypatch.setattr(post_content_worker, "post_content_is_complete", incomplete)

    row = asyncio.run(
        post_content_worker._claim_job(
            pool,
            "00000000-0000-0000-0000-000000000001",
            "a" * 64,
            embedding_model_code="text-embedding-3-large",
            require_structure=True,
        )
    )

    assert row is not None
    assert calls == ["00000000-0000-0000-0000-000000000001:text-embedding-3-large"]
    assert len(pool.connection.executed) == 3


def test_worker_skips_successful_job_only_when_complete(monkeypatch) -> None:
    pool = _Pool()

    async def complete(
        _connection, _post_id: str, *, embedding_model_code: str, require_structure: bool
    ) -> bool:
        assert embedding_model_code == "text-embedding-3-large"
        assert require_structure is True
        return True

    monkeypatch.setattr(post_content_worker, "post_content_is_complete", complete)

    row = asyncio.run(
        post_content_worker._claim_job(
            pool,
            "00000000-0000-0000-0000-000000000001",
            "a" * 64,
            embedding_model_code="text-embedding-3-large",
            require_structure=True,
        )
    )

    assert row is None
    assert pool.connection.executed == []
