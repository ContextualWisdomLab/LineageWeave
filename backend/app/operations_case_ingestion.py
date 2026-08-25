"""Persist and project contextual-orchestrator operational case evidence."""

from __future__ import annotations

import hashlib
from typing import Any, Protocol

from lineageweave.operations_case_analysis import OperationsCase


class _Connection(Protocol):
    def transaction(self) -> Any:
        """Open an atomic database transaction."""
        pass

    async def execute(self, query: str, *args: object) -> Any:
        """Execute one parameterized statement."""
        pass

    async def executemany(self, query: str, args: list[tuple[object, ...]]) -> Any:
        """Execute one parameterized statement for several rows."""
        pass


def source_body_digest(body: str) -> str:
    """Return the digest that binds inference to an exact source body."""
    return hashlib.sha256(body.encode("utf-8")).hexdigest()


async def persist_operations_cases(
    conn: _Connection,
    post_id: str,
    source_body: str,
    orchestrator_session_id: str,
    cases: tuple[OperationsCase, ...],
) -> None:
    """Atomically replace one post's normalized case analysis."""
    async with conn.transaction():
        await conn.execute("delete from operations_case_analysis where post_id = $1", post_id)
        await conn.execute(
            "insert into operations_case_analysis (post_id, source_body_sha256, orchestrator_session_id) values ($1, $2, $3)",
            post_id,
            source_body_digest(source_body),
            orchestrator_session_id,
        )
        for case in cases:
            await conn.execute(
                "insert into operations_case_classification (post_id, case_kind_code, summary_text, evidence_text) values ($1, $2, $3, $4)",
                post_id,
                case.case_kind_code,
                case.summary_text,
                case.evidence_text,
            )
            if case.facts:
                await conn.executemany(
                    "insert into operations_case_fact (post_id, case_kind_code, fact_ordinal, fact_type_code, value_text, evidence_text) values ($1, $2, $3, $4, $5, $6)",
                    [
                        (post_id, case.case_kind_code, ordinal, fact.fact_type_code, fact.value_text, fact.evidence_text)
                        for ordinal, fact in enumerate(case.facts)
                    ],
                )
