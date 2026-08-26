from __future__ import annotations

import asyncio

from lineageweave.post_content_persistence import persist_post_content


class _Transaction:
    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, traceback):
        return False


class _Connection:
    def __init__(self) -> None:
        self.executed: list[tuple[str, tuple[object, ...]]] = []
        self.fetched: list[str] = []

    def transaction(self) -> _Transaction:
        return _Transaction()

    async def execute(self, query: str, *args: object) -> str:
        self.executed.append((query, args))
        return "OK"

    async def fetchval(self, query: str, *args: object) -> str:
        self.fetched.append(query)
        if "post_content_unit" in query:
            return "unit-1"
        return "embedding-1"


class _EmbeddingClient:
    available = True
    resolved_model = "resolved-embedding"

    def embed_many(self, texts: list[str]) -> list[list[float]]:
        return [[0.1, 0.2] for _ in texts]


class _FailingEmbeddingClient:
    available = True
    resolved_model = None

    def embed_many(self, texts: list[str]) -> list[list[float]]:
        raise RuntimeError("synthetic provider outage")


def test_persist_post_content_writes_units_and_validated_vectors() -> None:
    conn = _Connection()

    unit_count = asyncio.run(
        persist_post_content(
            conn,
            "post-1",
            "A paragraph with a meaningful retrieval unit.",
            embedding_client=_EmbeddingClient(),
        )
    )

    assert unit_count == 1
    assert any("delete from post_content_unit" in query for query, _args in conn.executed)
    assert any("post_content_embedding_value" in query for query, _args in conn.executed)
    assert any("post_content_embedding" in query for query in conn.fetched)


def test_persist_post_content_keeps_units_when_embedding_provider_fails() -> None:
    conn = _Connection()

    unit_count = asyncio.run(
        persist_post_content(
            conn,
            "post-1",
            "A paragraph that remains searchable without a vector.",
            embedding_client=_FailingEmbeddingClient(),
        )
    )

    assert unit_count == 1
    assert any("post_content_unit" in query for query, _args in conn.executed)
    assert not any("post_content_embedding_value" in query for query, _args in conn.executed)
