"""Persist and project contextual-orchestrator operational case evidence."""

from __future__ import annotations

from typing import Any, Protocol

from backend.app.post_content_queue import source_body_sha256
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
    """Return the digest that binds inference to an exact focal source body."""
    return source_body_sha256(body)


async def persist_operations_cases(
    conn: _Connection,
    post_id: str,
    source_body: str,
    orchestrator_session_id: str,
    cases: tuple[OperationsCase, ...],
) -> None:
    """Atomically replace one post's normalized case analysis."""
    async with conn.transaction():
        await conn.execute(
            "delete from operations_case_analysis where post_id = $1", post_id
        )
        await conn.execute(
            "insert into operations_case_analysis (post_id, source_body_sha256, orchestrator_session_id) values ($1, $2, $3)",
            post_id,
            source_body_sha256(source_body),
            orchestrator_session_id,
        )
        for case in cases:
            await conn.execute(
                "insert into operations_case_classification (post_id, case_kind_code, summary_text, evidence_text, evidence_post_id, evidence_input_sha256) values ($1, $2, $3, $4, $5, $6)",
                post_id,
                case.case_kind_code,
                case.summary_text,
                case.evidence_text,
                case.evidence_post_id,
                case.evidence_input_sha256,
            )
            if case.facts:
                await conn.executemany(
                    "insert into operations_case_fact (post_id, case_kind_code, fact_ordinal, fact_type_code, value_text, evidence_text, evidence_post_id, evidence_input_sha256, relation_target_kind_code) values ($1, $2, $3, $4, $5, $6, $7, $8, $9)",
                    [
                        (post_id, case.case_kind_code, ordinal, fact.fact_type_code, fact.value_text, fact.evidence_text, fact.evidence_post_id, fact.evidence_input_sha256, fact.relation_target_kind_code)
                        for ordinal, fact in enumerate(case.facts)
                    ],
                )
            if case.missing_fact_type_codes:
                await conn.executemany(
                    "insert into operations_case_missing_fact (post_id, case_kind_code, fact_type_code) values ($1, $2, $3)",
                    [
                        (post_id, case.case_kind_code, code)
                        for code in case.missing_fact_type_codes
                    ],
                )
            if case.milestones:
                await conn.executemany(
                    "insert into operations_case_milestone (post_id, case_kind_code, milestone_type_code, evidence_text, evidence_post_id, evidence_input_sha256, observed_at, time_axis_code) values ($1, $2, $3, $4, $5, $6, $7, $8)",
                    [
                        (
                            post_id,
                            case.case_kind_code,
                            milestone.milestone_type_code,
                            milestone.evidence_text,
                            milestone.evidence_post_id,
                            milestone.evidence_input_sha256,
                            milestone.observed_at,
                            milestone.time_axis_code,
                        )
                        for milestone in case.milestones
                    ],
                )
            if case.missing_milestone_type_codes:
                await conn.executemany(
                    "insert into operations_case_missing_milestone (post_id, case_kind_code, milestone_type_code) values ($1, $2, $3)",
                    [
                        (post_id, case.case_kind_code, code)
                        for code in case.missing_milestone_type_codes
                    ],
                )
