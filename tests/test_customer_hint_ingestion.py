"""Tests for backend.app.customer_hint_ingestion.

Deterministic FakeConnection, same style as
tests/test_organization_name_resolution_ingestion.py.
"""

from __future__ import annotations

import asyncio
from types import SimpleNamespace

import backend.app.customer_hint_ingestion as ingestion
from lineageweave.relation_verification import (
    STATUS_CORROBORATED,
    STATUS_UNCORROBORATED,
)


class _AvailableClient:
    available = True


class _UnavailableClient:
    available = False


class _CustomerHintConnection:
    def __init__(self, *, source_post_rows=None, existing_entity_row=None) -> None:
        self._source_post_rows = source_post_rows or []
        self._existing_entity_row = existing_entity_row
        self.executed: list[tuple[str, tuple[object, ...]]] = []

    async def fetch(self, sql_query: str, *query_arguments: object):
        if "from source_post" in sql_query:
            return self._source_post_rows
        if "update source_post" in sql_query:
            self.executed.append((sql_query, query_arguments))
            return [{"post_id": "post-1"}, {"post_id": "post-2"}]
        return []

    async def fetchrow(self, sql_query: str, *query_arguments: object):
        if "from corporate_entity" in sql_query:
            return self._existing_entity_row
        if "insert into corporate_entity" in sql_query:
            self.executed.append((sql_query, query_arguments))
            return {"corporate_entity_id": "new-entity-id"}
        return None


def _verified_resolution(verification_status_code: str):
    return SimpleNamespace(
        raw_organization_name="0019999999",
        resolved_organization_name="Northridge Grid",
        verification_status_code=verification_status_code,
        verification_evidence_url=(
            "https://evidence.example/result"
            if verification_status_code == STATUS_CORROBORATED
            else None
        ),
    )


def test_unavailable_client_resolves_nothing() -> None:
    database_connection = _CustomerHintConnection()
    resolution_result = asyncio.run(
        ingestion.resolve_customer_hint(
            database_connection,
            _UnavailableClient(),
            _AvailableClient(),
            "0019999999",
        )
    )
    assert resolution_result is None


def test_no_sample_posts_resolves_nothing() -> None:
    database_connection = _CustomerHintConnection(source_post_rows=[])
    resolution_result = asyncio.run(
        ingestion.resolve_customer_hint(
            database_connection,
            _AvailableClient(),
            _AvailableClient(),
            "0019999999",
        )
    )
    assert resolution_result is None


def test_uncorroborated_resolution_does_not_create_or_link_an_entity(
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        ingestion,
        "resolve_and_verify_organization_name",
        lambda *_call_arguments: _verified_resolution(STATUS_UNCORROBORATED),
    )
    database_connection = _CustomerHintConnection(
        source_post_rows=[{"post_title": "Visit", "post_body": "<p>Visit notes</p>"}]
    )
    resolution_result = asyncio.run(
        ingestion.resolve_customer_hint(
            database_connection,
            _AvailableClient(),
            _AvailableClient(),
            "0019999999",
        )
    )

    assert resolution_result is None
    assert database_connection.executed == []


def test_corroborated_resolution_creates_and_links_a_new_entity(monkeypatch) -> None:
    monkeypatch.setattr(
        ingestion,
        "resolve_and_verify_organization_name",
        lambda *_call_arguments: _verified_resolution(STATUS_CORROBORATED),
    )
    database_connection = _CustomerHintConnection(
        source_post_rows=[{"post_title": "Visit", "post_body": "<p>Visit notes</p>"}]
    )
    resolution_result = asyncio.run(
        ingestion.resolve_customer_hint(
            database_connection,
            _AvailableClient(),
            _AvailableClient(),
            "0019999999",
        )
    )

    assert resolution_result == {
        "corporate_entity_id": "new-entity-id",
        "entity_name": "Northridge Grid",
        "linked_post_count": 2,
        "verification_evidence_url": "https://evidence.example/result",
    }
    entity_insert_calls = [
        executed_call
        for executed_call in database_connection.executed
        if "insert into corporate_entity" in executed_call[0]
    ]
    assert len(entity_insert_calls) == 1
    assert entity_insert_calls[0][1] == ("HINT-0019999999", "Northridge Grid")
    # Live-shaped bug: re-resolving the same hint_code is not guaranteed to
    # get byte-identical LLM phrasing back, so the create path must key off
    # corporate_entity_code (deterministic from hint_code), not rely on the
    # name-based lookup alone -- otherwise a second resolve with slightly
    # different wording collides on the unique code and raises uncaught.
    assert "on conflict (corporate_entity_code)" in entity_insert_calls[0][0]


def test_corroborated_resolution_reuses_an_existing_entity_by_name(monkeypatch) -> None:
    monkeypatch.setattr(
        ingestion,
        "resolve_and_verify_organization_name",
        lambda *_call_arguments: _verified_resolution(STATUS_CORROBORATED),
    )
    database_connection = _CustomerHintConnection(
        source_post_rows=[{"post_title": "Visit", "post_body": "<p>Visit notes</p>"}],
        existing_entity_row={"corporate_entity_id": "existing-entity-id"},
    )
    resolution_result = asyncio.run(
        ingestion.resolve_customer_hint(
            database_connection,
            _AvailableClient(),
            _AvailableClient(),
            "0019999999",
        )
    )

    assert resolution_result["corporate_entity_id"] == "existing-entity-id"
    assert all(
        "insert into corporate_entity" not in executed_call[0]
        for executed_call in database_connection.executed
    )
