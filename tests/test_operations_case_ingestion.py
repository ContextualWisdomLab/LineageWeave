"""Operational case persistence tests."""

import asyncio
from datetime import UTC, datetime

from backend.app.operations_case_ingestion import (
    persist_operations_cases,
    source_body_digest,
)
from lineageweave.operations_case_analysis import (
    OperationsCase,
    OperationsCaseFact,
    OperationsCaseMilestone,
)


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
    digest = "a" * 64
    cases = (
        OperationsCase(
            "claim_investigation",
            "Claim",
            "source",
            (OperationsCaseFact("order", "A-1", "source", "post-1", digest),),
            "post-1",
            digest,
        ),
    )
    asyncio.run(persist_operations_cases(conn, "post-1", "source", "session-1", cases))
    assert len(source_body_digest("source")) == 64
    assert "delete from operations_case_analysis" in conn.calls[0][0]
    assert conn.batches == [
        [
            (
                "post-1",
                "claim_investigation",
                0,
                "order",
                "A-1",
                "source",
                "post-1",
                digest,
            )
        ]
    ]


def test_persists_supported_empty_analysis() -> None:
    """A completed no-case result is recorded without fabricated children."""
    conn = _Connection()
    asyncio.run(persist_operations_cases(conn, "post-1", "ordinary", "session-1", ()))
    assert len(conn.calls) == 2
    assert conn.batches == []


def test_persists_missing_required_facts_without_invented_evidence() -> None:
    """Unsupported answers use the normalized missing-fact relation only."""
    conn = _Connection()
    case = OperationsCase(
        "claim_investigation",
        "Claim",
        "source",
        (),
        "post-1",
        "a" * 64,
        ("order", "specification_change", "originating_order", "sales_pool"),
    )

    asyncio.run(
        persist_operations_cases(conn, "post-1", "source", "session-1", (case,))
    )

    assert conn.batches == [
        [
            ("post-1", "claim_investigation", "order"),
            ("post-1", "claim_investigation", "specification_change"),
            ("post-1", "claim_investigation", "originating_order"),
            ("post-1", "claim_investigation", "sales_pool"),
        ]
    ]


def test_persists_observed_and_missing_milestones_separately() -> None:
    """An observed source instant is never replaced by an invented endpoint."""
    conn = _Connection()
    observed_at = datetime(2026, 8, 1, tzinfo=UTC)
    case = OperationsCase(
        "claim_investigation",
        "Claim",
        "source",
        (),
        "post-1",
        "a" * 64,
        ("order", "specification_change", "originating_order", "sales_pool"),
        (
            OperationsCaseMilestone(
                "claim_received",
                "source",
                "post-1",
                "a" * 64,
                observed_at,
                "event_occurred_at",
            ),
        ),
        ("cause_confirmed",),
    )

    asyncio.run(
        persist_operations_cases(conn, "post-1", "source", "session-1", (case,))
    )

    assert conn.batches[-2] == [
        (
            "post-1",
            "claim_investigation",
            "claim_received",
            "source",
            "post-1",
            "a" * 64,
            observed_at,
            "event_occurred_at",
        )
    ]
    assert conn.batches[-1] == [("post-1", "claim_investigation", "cause_confirmed")]
