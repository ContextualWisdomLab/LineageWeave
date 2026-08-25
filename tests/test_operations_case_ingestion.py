"""Operational case persistence tests."""

import asyncio

from backend.app.operations_case_ingestion import persist_operations_cases, source_body_digest
from lineageweave.operations_case_analysis import OperationsCase, OperationsCaseFact


class _Transaction:
    async def __aenter__(self):
        return self

    async def __aexit__(self, *_args: object) -> None:
        return None


class _Connection:
    def __init__(self) -> None:
        self.calls: list[tuple[str, tuple[object, ...]]] = []
        self.batches: list[list[tuple[object, ...]]] = []

    def transaction(self) -> _Transaction:
        return _Transaction()

    async def execute(self, sql: str, *args: object) -> None:
        self.calls.append((sql, args))

    async def executemany(self, _sql: str, args: list[tuple[object, ...]]) -> None:
        self.batches.append(args)


def test_digest_and_atomic_normalized_persistence() -> None:
    """The parent, classifications, and facts retain exact-body lineage."""
    conn = _Connection()
    cases = (OperationsCase("claim_investigation", "Claim", "source", (OperationsCaseFact("order", "A-1", "source"),)),)
    asyncio.run(persist_operations_cases(conn, "post-1", "source", "session-1", cases))
    assert len(source_body_digest("source")) == 64
    assert "delete from operations_case_analysis" in conn.calls[0][0]
    assert conn.batches == [[("post-1", "claim_investigation", 0, "order", "A-1", "source")]]


def test_persists_supported_empty_analysis() -> None:
    """A completed no-case result is recorded without fabricated children."""
    conn = _Connection()
    asyncio.run(persist_operations_cases(conn, "post-1", "ordinary", "session-1", ()))
    assert len(conn.calls) == 2
    assert conn.batches == []
