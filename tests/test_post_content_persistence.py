from __future__ import annotations

import asyncio
import hashlib

from lineageweave.post_content_persistence import persist_post_content


class _Transaction:
    def __init__(self, owner: _Connection) -> None:
        self.owner = owner

    async def __aenter__(self):
        self.owner.in_transaction = True
        return self

    async def __aexit__(self, exc_type, exc, traceback):
        self.owner.in_transaction = False
        return False


class _Connection:
    def __init__(self, claim_row: dict[str, object] | None = None) -> None:
        self.executed: list[tuple[str, tuple[object, ...]]] = []
        self.fetched: list[str] = []
        self.claim_row = claim_row
        self.in_transaction = False

    def transaction(self) -> _Transaction:
        return _Transaction(self)

    async def execute(self, query: str, *args: object) -> str:
        self.executed.append((query, args))
        return "OK"

    async def fetchval(self, query: str, *args: object) -> str:
        self.fetched.append(query)
        if "post_content_unit" in query:
            return "unit-1"
        return "embedding-1"

    async def fetchrow(self, query: str, *args: object):
        self.fetched.append(query)
        return self.claim_row


class _EmbeddingClient:
    available = True

    def embed_many(self, texts: list[str]) -> list[list[float]]:
        return [[0.1, 0.2] for _ in texts]


class _FailingEmbeddingClient:
    available = True

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
            embedding_model_code="text-embedding-3-large",
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
            embedding_model_code="text-embedding-3-large",
        )
    )

    assert unit_count == 1
    assert any("post_content_unit" in query for query, _args in conn.executed)
    assert not any("post_content_embedding_value" in query for query, _args in conn.executed)


def test_stale_claim_cannot_replace_current_post_content_artifacts() -> None:
    body = "A synthetic source revision."
    digest = hashlib.sha256(body.encode("utf-8")).hexdigest()
    conn = _Connection(claim_row=None)

    unit_count = asyncio.run(
        persist_post_content(
            conn,
            "post-1",
            body,
            expected_source_body_sha256=digest,
            expected_attempt_count=7,
        )
    )

    assert unit_count is None
    assert any("for update of job, post" in query for query in conn.fetched)
    assert not any("delete from post_content_unit" in query for query, _args in conn.executed)


def test_claim_with_changed_source_body_cannot_replace_artifacts() -> None:
    body = "The source body used by an older worker."
    digest = hashlib.sha256(body.encode("utf-8")).hexdigest()
    conn = _Connection(claim_row={"post_body": "A newer source body."})

    unit_count = asyncio.run(
        persist_post_content(
            conn,
            "post-1",
            body,
            expected_source_body_sha256=digest,
            expected_attempt_count=8,
        )
    )

    assert unit_count is None
    assert not any("delete from post_content_unit" in query for query, _args in conn.executed)


def test_operator_fence_and_artifact_replacement_share_one_transaction() -> None:
    conn = _Connection()
    events: list[str] = []

    async def fence(inner_conn: _Connection) -> None:
        assert inner_conn is conn
        assert inner_conn.in_transaction
        events.append("fence")

    unit_count = asyncio.run(
        persist_post_content(
            conn,
            "post-1",
            "A synthetic backfill body.",
            transaction_fence=fence,
        )
    )

    assert unit_count == 1
    assert events == ["fence"]
    assert any("delete from post_content_unit" in query for query, _args in conn.executed)
