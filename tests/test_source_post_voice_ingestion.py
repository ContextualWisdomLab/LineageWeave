"""Evidence-bearing additional Voice persistence tests (ADR 0256)."""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from typing import Any

import pytest

from backend.app.source_post_voice_ingestion import (
    PrimaryVoiceAssignmentError,
    persist_additional_voice_assignment,
)


class _Connection:
    """Record the ordered SQL contract without requiring a live database."""

    def __init__(
        self,
        *,
        existing_evidence: bool = False,
        current: dict[str, object] | None = None,
    ) -> None:
        self.current = current
        self.calls: list[tuple[str, tuple[object, ...]]] = []
        self.fetchvals = iter(
            [
                "voc",
                "evidence-resource",
                "assignment-resource",
                "assertion",
                datetime(2026, 10, 1, tzinfo=UTC),
            ]
            if existing_evidence
            else [
                "voc",
                None,
                "evidence-resource",
                "evidence-resource",
                "assignment-resource",
                "assertion",
                datetime(2026, 10, 1, tzinfo=UTC),
            ]
        )

    @asynccontextmanager
    async def transaction(self):
        """Expose the async transaction protocol used by asyncpg."""
        yield

    async def execute(self, query: str, *args: object) -> None:
        """Record an execute call."""
        self.calls.append((query, args))

    async def fetchval(self, query: str, *args: object) -> Any:
        """Record and return the next scripted scalar."""
        self.calls.append((query, args))
        return next(self.fetchvals)

    async def fetchrow(self, query: str, *args: object) -> dict[str, object] | None:
        """Return the existing additional interval, if supplied."""
        self.calls.append((query, args))
        return self.current


def test_additional_voice_creates_prov_derivation_and_assignment_atomically() -> None:
    """The write derives an assignment from a bound evidence Post resource."""
    conn = _Connection()

    asyncio.run(
        persist_additional_voice_assignment(
            conn,
            post_id="aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa1",
            voice_type_code="vops",
            truth_status_code="truth_observed",
            evidence_post_id="aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa2",
        )
    )

    sql = "\n".join(query for query, _args in conn.calls)
    assert "prov_was_derived_from" in sql
    assert "and effective_to is null" in sql
    assert "for update" in sql
    assert "select clock_timestamp()" in sql
    assert "voice-assignment/aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa1/vops" in str(
        conn.calls
    )


def test_additional_voice_cannot_demote_imported_primary() -> None:
    """The current primary remains owned by source_post.voc_type_code."""
    conn = _Connection()

    with pytest.raises(PrimaryVoiceAssignmentError):
        asyncio.run(
            persist_additional_voice_assignment(
                conn,
                post_id="aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa1",
                voice_type_code="voc",
                truth_status_code="truth_observed",
                evidence_post_id="aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa2",
            )
        )


def test_existing_evidence_binding_is_typed_as_a_prov_entity() -> None:
    """A legacy Post binding gains the type required by PROV range checks."""
    conn = _Connection(existing_evidence=True)

    asyncio.run(
        persist_additional_voice_assignment(
            conn,
            post_id="aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa1",
            voice_type_code="vops",
            truth_status_code="truth_observed",
            evidence_post_id="aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa2",
        )
    )

    assert any(
        "provenance_resource_type" in query and args == ("evidence-resource",)
        for query, args in conn.calls
    )


def test_repeating_the_same_truth_and_evidence_retains_the_interval() -> None:
    """A retry cannot move the original availability clock or create history."""
    conn = _Connection(
        current={
            "voice_assignment_id": "current-assignment",
            "is_primary": False,
            "truth_status_code": "truth_observed",
            "provenance_assertion_id": "assertion",
        }
    )
    asyncio.run(
        persist_additional_voice_assignment(
            conn,
            post_id="aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa1",
            voice_type_code="vops",
            truth_status_code="truth_observed",
            evidence_post_id="aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa2",
        )
    )
    assert not any(
        "update source_post_voice" in query or "insert into source_post_voice" in query
        for query, _args in conn.calls
    )


def test_replacement_closes_only_the_previous_interval() -> None:
    """A new truth state keeps the old assertion and its recording time intact."""
    conn = _Connection(
        current={
            "voice_assignment_id": "old-assignment",
            "is_primary": False,
            "truth_status_code": "truth_proposed",
            "provenance_assertion_id": "old-assertion",
        }
    )
    asyncio.run(
        persist_additional_voice_assignment(
            conn,
            post_id="aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa1",
            voice_type_code="vops",
            truth_status_code="truth_observed",
            evidence_post_id="aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa2",
        )
    )
    close = next(
        (query, args)
        for query, args in conn.calls
        if "update source_post_voice" in query
    )
    insert = next(
        (query, args)
        for query, args in conn.calls
        if "insert into source_post_voice" in query
    )
    assert close[1][0] == "old-assignment"
    assert close[1][1] == insert[1][4]
    assert "recorded_at =" not in close[0]
    assert "truth_status_code =" not in close[0]
    assert "provenance_assertion_id =" not in close[0]
