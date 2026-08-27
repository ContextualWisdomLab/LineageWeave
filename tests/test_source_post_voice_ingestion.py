"""Evidence-bearing additional Voice persistence tests (ADR 0256)."""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from typing import Any

import pytest

from backend.app.source_post_voice_ingestion import (
    PrimaryVoiceAssignmentError,
    persist_additional_voice_assignment,
)


class _Connection:
    """Record the ordered SQL contract without requiring a live database."""

    def __init__(
        self, *, primary_conflict: bool = False, existing_evidence: bool = False
    ) -> None:
        self.primary_conflict = primary_conflict
        self.calls: list[tuple[str, tuple[object, ...]]] = []
        self.fetchvals = iter(
            ["evidence-resource", "assignment-resource", "assertion"]
            if existing_evidence
            else [
                None,
                "evidence-resource",
                "evidence-resource",
                "assignment-resource",
                "assertion",
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

    async def fetchrow(self, query: str, *args: object) -> dict[str, str] | None:
        """Return no row only when the imported primary blocks the write."""
        self.calls.append((query, args))
        return None if self.primary_conflict else {"voice_type_code": str(args[1])}


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
    assert "where effective_to is null" in sql
    assert "where not source_post_voice.is_primary" in sql
    assert "voice-assignment/aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa1/vops" in str(
        conn.calls
    )


def test_additional_voice_cannot_demote_imported_primary() -> None:
    """The current primary remains owned by source_post.voc_type_code."""
    conn = _Connection(primary_conflict=True)

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
