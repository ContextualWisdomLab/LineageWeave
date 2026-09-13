"""Tests for backend.app.customer_hint_ingestion."""

from __future__ import annotations

import asyncio
from types import SimpleNamespace

import backend.app.customer_hint_ingestion as ingestion
from lineageweave.relation_verification import STATUS_CORROBORATED, STATUS_UNCORROBORATED


class _Client:
    available = True


class _UnavailableClient:
    available = False


class _Transaction:
    async def __aenter__(self):
        return self

    async def __aexit__(self, *_exc):
        return False


class _Acquire:
    def __init__(self, connection) -> None:
        self.connection = connection

    async def __aenter__(self):
        return self.connection

    async def __aexit__(self, *_exc):
        return False


class _Pool:
    def __init__(self, connection) -> None:
        self.connection = connection
        self.acquire_count = 0

    def acquire(self):
        self.acquire_count += 1
        return _Acquire(self.connection)


class _Connection:
    def __init__(self, *, sample_rows=None, existing_entity=None) -> None:
        self._sample_rows = sample_rows or []
        self._existing_entity = existing_entity
        self.executed: list[tuple[str, tuple[object, ...]]] = []

    def transaction(self):
        return _Transaction()

    async def fetch(self, query: str, *args: object):
        normalized = " ".join(query.lower().split())
        self.executed.append((normalized, args))
        if "select post_id, post_title" in normalized:
            return self._sample_rows
        if "select post_id from source_post" in normalized and "for share" in normalized:
            return [{"post_id": row["post_id"]} for row in self._sample_rows]
        if "insert into source_post_customer_resolution" in normalized:
            return [{"post_id": row["post_id"]} for row in self._sample_rows]
        return []

    async def fetchrow(self, query: str, *args: object):
        normalized = " ".join(query.lower().split())
        self.executed.append((normalized, args))
        if "from corporate_entity" in normalized:
            return self._existing_entity
        if "insert into corporate_entity" in normalized:
            return {"corporate_entity_id": "new-entity-id"}
        return None


def _resolution(status: str):
    return SimpleNamespace(
        raw_organization_name="0019999999",
        resolved_organization_name="Northridge Grid",
        verification_status_code=status,
        verification_evidence_url=(
            "https://evidence.example/result" if status == STATUS_CORROBORATED else None
        ),
    )


def _resolve(pool, resolution_client=_Client()):
    return ingestion.resolve_customer_hint(
        pool,
        resolution_client,
        _Client(),
        "0019999999",
        ["corp-a"],
        ["pu-a"],
    )


def test_unavailable_client_resolves_nothing() -> None:
    connection = _Connection()
    pool = _Pool(connection)
    result = asyncio.run(_resolve(pool, _UnavailableClient()))
    assert result is None
    assert pool.acquire_count == 0


def test_no_visible_sample_posts_resolves_nothing() -> None:
    pool = _Pool(_Connection(sample_rows=[]))
    result = asyncio.run(_resolve(pool))
    assert result is None
    assert pool.acquire_count == 1


def test_uncorroborated_resolution_does_not_create_or_persist(monkeypatch) -> None:
    monkeypatch.setattr(
        ingestion,
        "resolve_and_verify_organization_name",
        lambda *_args: _resolution(STATUS_UNCORROBORATED),
    )
    connection = _Connection(
        sample_rows=[
            {"post_id": "post-1", "post_title": "Visit", "post_body": "<p>Visit notes</p>"}
        ]
    )
    pool = _Pool(connection)
    result = asyncio.run(_resolve(pool))

    assert result is None
    assert pool.acquire_count == 1
    assert all("insert into corporate_entity" not in query for query, _ in connection.executed)
    assert all(
        "insert into source_post_customer_resolution" not in query
        for query, _ in connection.executed
    )


def test_corroborated_resolution_creates_separate_association(monkeypatch) -> None:
    monkeypatch.setattr(
        ingestion,
        "resolve_and_verify_organization_name",
        lambda *_args: _resolution(STATUS_CORROBORATED),
    )
    connection = _Connection(
        sample_rows=[
            {"post_id": "post-1", "post_title": "Visit", "post_body": "<p>Visit notes</p>"}
        ]
    )
    pool = _Pool(connection)
    result = asyncio.run(_resolve(pool))

    assert result == {
        "corporate_entity_id": "new-entity-id",
        "entity_name": "Northridge Grid",
        "linked_post_count": 1,
        "verification_evidence_url": "https://evidence.example/result",
    }
    assert pool.acquire_count == 2
    assert all("update source_post" not in query for query, _ in connection.executed)
    assert any(
        "insert into source_post_customer_resolution" in query
        for query, _ in connection.executed
    )


def test_corroborated_resolution_reuses_existing_catalog_entity(monkeypatch) -> None:
    monkeypatch.setattr(
        ingestion,
        "resolve_and_verify_organization_name",
        lambda *_args: _resolution(STATUS_CORROBORATED),
    )
    connection = _Connection(
        sample_rows=[
            {"post_id": "post-1", "post_title": "Visit", "post_body": "<p>Visit notes</p>"}
        ],
        existing_entity={"corporate_entity_id": "existing-entity-id"},
    )
    result = asyncio.run(_resolve(_Pool(connection)))

    assert result["corporate_entity_id"] == "existing-entity-id"
    assert all("insert into corporate_entity" not in query for query, _ in connection.executed)


def test_scope_change_between_capture_and_persistence_fails_closed(monkeypatch) -> None:
    monkeypatch.setattr(
        ingestion,
        "resolve_and_verify_organization_name",
        lambda *_args: _resolution(STATUS_CORROBORATED),
    )

    class _ChangedConnection(_Connection):
        async def fetch(self, query: str, *args: object):
            normalized = " ".join(query.lower().split())
            self.executed.append((normalized, args))
            if "select post_id, post_title" in normalized:
                return self._sample_rows
            if "for share" in normalized:
                return []
            return []

    connection = _ChangedConnection(
        sample_rows=[
            {"post_id": "post-1", "post_title": "Visit", "post_body": "<p>Visit notes</p>"}
        ]
    )
    result = asyncio.run(_resolve(_Pool(connection)))

    assert result is None
    assert all("insert into corporate_entity" not in query for query, _ in connection.executed)
