"""Tests for backend.app.customer_hint_ingestion.

Deterministic FakeConnection, same style as
tests/test_organization_name_resolution_ingestion.py.
"""

from __future__ import annotations

import asyncio
from types import SimpleNamespace

import backend.app.customer_hint_ingestion as ingestion
from lineageweave.relation_verification import STATUS_CORROBORATED, STATUS_UNCORROBORATED


class _Client:
    available = True


class _UnavailableClient:
    available = False


class _Connection:
    def __init__(self, *, sample_rows=None, existing_entity=None) -> None:
        self._sample_rows = sample_rows or []
        self._existing_entity = existing_entity
        self.executed: list[tuple[str, tuple[object, ...]]] = []

    async def fetch(self, query: str, *args: object):
        if "from source_post" in query:
            return self._sample_rows
        if "update source_post" in query:
            self.executed.append((query, args))
            return [{"post_id": "post-1"}, {"post_id": "post-2"}]
        return []

    async def fetchrow(self, query: str, *args: object):
        if "from corporate_entity" in query:
            return self._existing_entity
        if "insert into corporate_entity" in query:
            self.executed.append((query, args))
            return {"corporate_entity_id": "new-entity-id"}
        return None


def _resolution(status: str):
    return SimpleNamespace(
        raw_organization_name="0019999999",
        resolved_organization_name="Northridge Grid",
        verification_status_code=status,
        verification_evidence_url="https://evidence.example/result" if status == STATUS_CORROBORATED else None,
    )


def test_unavailable_client_resolves_nothing() -> None:
    conn = _Connection()
    result = asyncio.run(
        ingestion.resolve_customer_hint(conn, _UnavailableClient(), _Client(), "0019999999")
    )
    assert result is None


def test_placeholder_hint_never_enters_resolution_or_catalog() -> None:
    """A generic source category stays a weak hint, never an identity request."""

    class ForbiddenConnection:
        async def fetch(self, *_args: object) -> None:
            raise AssertionError("placeholder hint must not read source bodies")

    result = asyncio.run(
        ingestion.resolve_customer_hint(
            ForbiddenConnection(),  # type: ignore[arg-type]
            _Client(),
            _Client(),
            "기타",
        )
    )

    assert result is None


def test_no_sample_posts_resolves_nothing() -> None:
    conn = _Connection(sample_rows=[])
    result = asyncio.run(ingestion.resolve_customer_hint(conn, _Client(), _Client(), "0019999999"))
    assert result is None


def test_uncorroborated_resolution_does_not_create_or_link_an_entity(monkeypatch) -> None:
    monkeypatch.setattr(
        ingestion, "resolve_and_verify_organization_name", lambda *_args: _resolution(STATUS_UNCORROBORATED)
    )
    conn = _Connection(sample_rows=[{"post_title": "Visit", "post_body": "<p>Visit notes</p>"}])
    result = asyncio.run(ingestion.resolve_customer_hint(conn, _Client(), _Client(), "0019999999"))

    assert result is None
    assert conn.executed == []


def test_corroborated_resolution_creates_and_links_a_new_entity(monkeypatch) -> None:
    monkeypatch.setattr(
        ingestion, "resolve_and_verify_organization_name", lambda *_args: _resolution(STATUS_CORROBORATED)
    )
    conn = _Connection(sample_rows=[{"post_title": "Visit", "post_body": "<p>Visit notes</p>"}])
    result = asyncio.run(ingestion.resolve_customer_hint(conn, _Client(), _Client(), "0019999999"))

    assert result == {
        "corporate_entity_id": "new-entity-id",
        "entity_name": "Northridge Grid",
        "linked_post_count": 2,
        "verification_evidence_url": "https://evidence.example/result",
    }
    insert_calls = [call for call in conn.executed if "insert into corporate_entity" in call[0]]
    assert len(insert_calls) == 1
    assert insert_calls[0][1] == ("HINT-0019999999", "Northridge Grid")
    # Live-shaped bug: re-resolving the same hint_code is not guaranteed to
    # get byte-identical LLM phrasing back, so the create path must key off
    # corporate_entity_code (deterministic from hint_code), not rely on the
    # name-based lookup alone -- otherwise a second resolve with slightly
    # different wording collides on the unique code and raises uncaught.
    assert "on conflict (corporate_entity_code)" in insert_calls[0][0]


def test_corroborated_resolution_reuses_an_existing_entity_by_name(monkeypatch) -> None:
    monkeypatch.setattr(
        ingestion, "resolve_and_verify_organization_name", lambda *_args: _resolution(STATUS_CORROBORATED)
    )
    conn = _Connection(
        sample_rows=[{"post_title": "Visit", "post_body": "<p>Visit notes</p>"}],
        existing_entity={"corporate_entity_id": "existing-entity-id"},
    )
    result = asyncio.run(ingestion.resolve_customer_hint(conn, _Client(), _Client(), "0019999999"))

    assert result["corporate_entity_id"] == "existing-entity-id"
    assert all("insert into corporate_entity" not in call[0] for call in conn.executed)
