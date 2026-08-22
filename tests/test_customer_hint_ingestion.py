"""Tests for backend.app.customer_hint_ingestion.

Deterministic FakeConnection, same style as
tests/test_organization_name_resolution_ingestion.py.
Entity creation with a real hierarchy placement (inference, similarity
matching, the advisory-lock insert) is
`get_or_create_corporate_entity`'s own responsibility and is covered by
its own tests -- these tests monkeypatch it to isolate
`resolve_customer_hint`'s wiring, its unresolved/fail-closed branches, and
its flat-entity fallback for when a hierarchy placement is declined.
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


def _fake_load_candidates(candidates: list[object] | None = None):
    async def _load(conn):
        return candidates or []

    return _load


def test_unavailable_client_resolves_nothing() -> None:
    conn = _Connection()
    result = asyncio.run(
        ingestion.resolve_customer_hint(conn, _UnavailableClient(), _Client(), _Client(), "0019999999")
    )
    assert result is None


def test_no_sample_posts_resolves_nothing() -> None:
    conn = _Connection(sample_rows=[])
    result = asyncio.run(
        ingestion.resolve_customer_hint(conn, _Client(), _Client(), _Client(), "0019999999")
    )
    assert result is None


def test_uncorroborated_resolution_does_not_create_or_link_an_entity(monkeypatch) -> None:
    monkeypatch.setattr(
        ingestion, "resolve_and_verify_organization_name", lambda *_args: _resolution(STATUS_UNCORROBORATED)
    )
    conn = _Connection(sample_rows=[{"post_title": "Visit", "post_body": "<p>Visit notes</p>"}])
    result = asyncio.run(
        ingestion.resolve_customer_hint(conn, _Client(), _Client(), _Client(), "0019999999")
    )

    assert result is None
    assert conn.executed == []


def test_corroborated_resolution_uses_the_hierarchy_aware_placement(monkeypatch) -> None:
    # When get_or_create_corporate_entity finds or creates a placement
    # (a real hierarchy chain, or a fuzzy-matched existing entity), that
    # id is used as-is -- no flat fallback insert runs.
    monkeypatch.setattr(
        ingestion, "resolve_and_verify_organization_name", lambda *_args: _resolution(STATUS_CORROBORATED)
    )
    monkeypatch.setattr(ingestion, "_load_corporate_entity_candidates", _fake_load_candidates())

    async def fake_get_or_create(conn, entity_name, context_text, hierarchy_client, verification_client, candidates):
        assert entity_name == "Northridge Grid"
        return "hierarchy-placed-entity-id"

    monkeypatch.setattr(ingestion, "get_or_create_corporate_entity", fake_get_or_create)
    conn = _Connection(sample_rows=[{"post_title": "Visit", "post_body": "<p>Visit notes</p>"}])
    result = asyncio.run(
        ingestion.resolve_customer_hint(conn, _Client(), _Client(), _Client(), "0019999999")
    )

    assert result == {
        "corporate_entity_id": "hierarchy-placed-entity-id",
        "entity_name": "Northridge Grid",
        "linked_post_count": 2,
        "verification_evidence_url": "https://evidence.example/result",
    }
    assert all("insert into corporate_entity" not in call[0] for call in conn.executed)


def test_declined_hierarchy_placement_falls_back_to_a_flat_new_entity(monkeypatch) -> None:
    # No hierarchy-inference channel configured, a tied similarity match,
    # or an inferred placement that did not corroborate must not regress
    # an already name-corroborated hint back to fully unresolved -- it
    # falls back to the flat, unparented entity this pathway always
    # created before hierarchy inference existed.
    monkeypatch.setattr(
        ingestion, "resolve_and_verify_organization_name", lambda *_args: _resolution(STATUS_CORROBORATED)
    )
    monkeypatch.setattr(ingestion, "_load_corporate_entity_candidates", _fake_load_candidates())

    async def fake_get_or_create(conn, entity_name, context_text, hierarchy_client, verification_client, candidates):
        return None

    monkeypatch.setattr(ingestion, "get_or_create_corporate_entity", fake_get_or_create)
    conn = _Connection(sample_rows=[{"post_title": "Visit", "post_body": "<p>Visit notes</p>"}])
    result = asyncio.run(
        ingestion.resolve_customer_hint(conn, _Client(), _Client(), _Client(), "0019999999")
    )

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


def test_declined_hierarchy_placement_reuses_an_existing_entity_by_name(monkeypatch) -> None:
    monkeypatch.setattr(
        ingestion, "resolve_and_verify_organization_name", lambda *_args: _resolution(STATUS_CORROBORATED)
    )
    monkeypatch.setattr(ingestion, "_load_corporate_entity_candidates", _fake_load_candidates())

    async def fake_get_or_create(conn, entity_name, context_text, hierarchy_client, verification_client, candidates):
        return None

    monkeypatch.setattr(ingestion, "get_or_create_corporate_entity", fake_get_or_create)
    conn = _Connection(
        sample_rows=[{"post_title": "Visit", "post_body": "<p>Visit notes</p>"}],
        existing_entity={"corporate_entity_id": "existing-entity-id"},
    )
    result = asyncio.run(
        ingestion.resolve_customer_hint(conn, _Client(), _Client(), _Client(), "0019999999")
    )

    assert result["corporate_entity_id"] == "existing-entity-id"
    assert all("insert into corporate_entity" not in call[0] for call in conn.executed)
