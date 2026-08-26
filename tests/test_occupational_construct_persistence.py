"""Persistence checks for evidence-bound occupational constructs (ADR 0249)."""

from __future__ import annotations

import asyncio
from contextlib import AbstractAsyncContextManager
from datetime import UTC, datetime

import pytest

from backend.app.occupational_construct_ingestion import (
    ConstructVocabulary,
    OccupationalConstruct,
    OccupationalConstructAssertion,
    load_occupational_construct_assertions,
    persist_occupational_construct_assertions,
)


class _Transaction(AbstractAsyncContextManager[None]):
    async def __aenter__(self) -> None:
        return None

    async def __aexit__(self, *_args: object) -> None:
        return None


class RecordingConnection:
    """Record parameterized persistence calls without a database."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, tuple[object, ...]]] = []
        self.values = iter(("vocabulary-id", "construct-id"))
        self.rows: list[dict[str, object]] = []

    def transaction(self) -> _Transaction:
        return _Transaction()

    async def execute(self, query: str, *args: object) -> None:
        self.calls.append((" ".join(query.split()), args))

    async def fetchval(self, query: str, *args: object) -> str:
        self.calls.append((" ".join(query.split()), args))
        return next(self.values)

    async def fetch(self, query: str, *args: object) -> list[dict[str, object]]:
        self.calls.append((" ".join(query.split()), args))
        return self.rows


def _assertion() -> OccupationalConstructAssertion:
    vocabulary = ConstructVocabulary(
        "https://www.onetcenter.org/database.html",
        "31.0",
        "https://creativecommons.org/licenses/by/4.0/",
        "O*NET 31.0 Database by USDOL/ETA.",
    )
    construct = OccupationalConstruct(
        vocabulary,
        "https://data.onetcenter.org/element/1.A.1.a.1",
        "cognitive_ability",
        "Oral Comprehension",
    )
    return OccupationalConstructAssertion(
        "11111111-1111-1111-1111-111111111111",
        "The record states a synthetic comprehension requirement.",
        construct,
        "synthetic comprehension requirement",
        "truth_inferred",
        "contextual_orchestrator_structured",
    )


def test_assertion_rejects_nonverbatim_evidence_and_unsafe_iris() -> None:
    """Trust-boundary values fail before any SQL can run."""
    assertion = _assertion()
    with pytest.raises(ValueError, match="verbatim"):
        OccupationalConstructAssertion(
            assertion.post_content_unit_id,
            assertion.unit_text,
            assertion.construct,
            "not present",
            assertion.truth_status_code,
            assertion.extraction_method,
        )
    with pytest.raises(ValueError, match="HTTPS"):
        ConstructVocabulary(
            "http://unsafe.example/vocabulary",
            "1",
            "https://example.test/license",
            "Synthetic attribution",
        )
    with pytest.raises(ValueError, match="truth status"):
        OccupationalConstructAssertion(
            assertion.post_content_unit_id,
            assertion.unit_text,
            assertion.construct,
            assertion.evidence_text,
            "truth_guessed",
            assertion.extraction_method,
        )


def test_persistence_replaces_then_upserts_versioned_registry_and_assertion() -> None:
    """One transaction performs delete, registry UPSERTs, then assertion insert."""
    conn = RecordingConnection()
    asyncio.run(
        persist_occupational_construct_assertions(
            conn,
            "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
            "post-session",
            (_assertion(),),
        )
    )
    statements = [query for query, _ in conn.calls]
    assert statements[0].startswith("delete from post_occupational_construct_assertion")
    assert "on conflict (vocabulary_iri, version_label) do update" in statements[1]
    assert "where occupational_construct_vocabulary.license_iri" in statements[1]
    assert "on conflict (vocabulary_id, construct_iri) do update" in statements[2]
    assert "where occupational_construct.construct_family_code" in statements[2]
    assert statements[3].startswith("insert into post_occupational_construct_assertion")
    assert conn.calls[3][1][-1] == "post-session"


def test_conflicting_version_metadata_fails_closed() -> None:
    """An existing release cannot be silently rewritten by an UPSERT."""
    conn = RecordingConnection()
    conn.values = iter((None,))
    with pytest.raises(ValueError, match="immutable version"):
        asyncio.run(
            persist_occupational_construct_assertions(
                conn,
                "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
                "post-session",
                (_assertion(),),
            )
        )


def test_empty_replacement_only_removes_stale_assertions() -> None:
    """Unavailable analysis writes no placeholder registry or assertion rows."""
    conn = RecordingConnection()
    asyncio.run(
        persist_occupational_construct_assertions(
            conn, "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa", "post-session", ()
        )
    )
    assert len(conn.calls) == 1
    assert conn.calls[0][0].startswith("delete from post_occupational_construct_assertion")


def test_empty_success_records_the_source_digest_in_the_same_transaction() -> None:
    """A valid empty model result is persisted without a placeholder assertion."""
    conn = RecordingConnection()
    asyncio.run(
        persist_occupational_construct_assertions(
            conn,
            "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
            "post-session",
            (),
            source_body_sha256="a" * 64,
        )
    )
    assert len(conn.calls) == 2
    assert conn.calls[1][0].startswith(
        "insert into post_occupational_construct_extraction"
    )
    assert conn.calls[1][1] == (
        "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
        "a" * 64,
        "post-session",
    )


def test_extraction_run_rejects_a_malformed_source_digest() -> None:
    """The application mirrors the database digest trust boundary."""
    with pytest.raises(ValueError, match="lowercase SHA-256"):
        asyncio.run(
            persist_occupational_construct_assertions(
                RecordingConnection(),
                "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
                "post-session",
                (),
                source_body_sha256="NOT-A-DIGEST",
            )
        )


def test_authorized_projection_omits_internal_ids_and_preserves_provenance() -> None:
    """The read model returns review fields in semantic-unit order."""
    conn = RecordingConnection()
    conn.rows = [
        {
            "construct_iri": "https://data.onetcenter.org/element/1.A.1.a.1",
            "construct_family_code": "cognitive_ability",
            "preferred_label": "Oral Comprehension",
            "vocabulary_iri": "https://www.onetcenter.org/database.html",
            "version_label": "31.0",
            "evidence_text": "synthetic evidence",
            "truth_status_code": "truth_inferred",
            "extraction_method": "contextual_orchestrator_structured",
            "generated_at": datetime(2026, 8, 27, tzinfo=UTC),
            "unit_index": 2,
        }
    ]
    result = asyncio.run(
        load_occupational_construct_assertions(
            conn, "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
        )
    )
    assert result[0]["vocabulary_version"] == "31.0"
    assert result[0]["provenance"] == (
        "post_occupational_construct_assertion.evidence_text"
    )
    assert "construct_id" not in result[0]
    assert "job.source_body_sha256 = extraction.source_body_sha256" in conn.calls[0][0]


@pytest.mark.parametrize(
    ("stored", "expected"),
    (("complete", "complete"), ("processing", "processing"), (None, "unavailable")),
)
def test_evidence_status_preserves_missing_vs_empty(stored, expected) -> None:
    """Only a matching run is complete; active work and absence remain distinct."""

    class StatusConnection:
        async def fetchval(self, query: str, post_id: str):
            assert "extraction.source_body_sha256 = job.source_body_sha256" in query
            assert query.index("when job.status_code") < query.index(
                "when extraction.source_body_sha256"
            )
            assert post_id == "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
            return stored

    assert (
        asyncio.run(
            load_occupational_construct_evidence_status(
                StatusConnection(), "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
            )
        )
        == expected
    )


def test_evidence_status_distinguishes_missing_setup_from_retryable_failure() -> None:
    """A missing analysis setup never tells the reader that retrying can help."""
    class StatusConnection:
        async def fetchval(self, _query: str, _post_id: str):
            return None

    assert asyncio.run(
        load_occupational_construct_evidence_status(
            StatusConnection(), "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
            evidence_configured=False,
        )
    ) == "setup_required"
