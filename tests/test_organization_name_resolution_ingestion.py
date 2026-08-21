from __future__ import annotations

import asyncio
from types import SimpleNamespace

import pytest

import backend.app.organization_name_resolution_ingestion as ingestion
from lineageweave.relation_verification import (
    STATUS_CORROBORATED,
    STATUS_UNCORROBORATED,
)


class _Connection:
    def __init__(self, cached: dict[str, str] | None = None) -> None:
        self.cached = cached
        self.executed: list[tuple[str, tuple[object, ...]]] = []

    async def fetchrow(self, _query: str, _raw_name: str, _context_sha256: str):
        return self.cached

    async def execute(self, query: str, *args: object) -> str:
        self.executed.append((query, args))
        return "OK"


class _Client:
    available = True


class _UnavailableClient:
    available = False


def _resolution(status: str):
    return SimpleNamespace(
        raw_organization_name="AGP",
        resolved_organization_name="Aurora Grid Power",
        verification_status_code=status,
        verification_evidence_url="https://evidence.example/result" if status == STATUS_CORROBORATED else None,
    )


def test_cached_verified_name_is_returned_without_resolution() -> None:
    conn = _Connection({"resolved_organization_name": "Aurora Grid Power", "verification_status_code": STATUS_CORROBORATED})
    result = asyncio.run(ingestion.resolve_organization_name(conn, _UnavailableClient(), _Client(), "AGP", "context"))
    assert result == "Aurora Grid Power"
    assert conn.executed == []


def test_cache_key_includes_context_digest(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(ingestion, "resolve_and_verify_organization_name", lambda *_args: _resolution(STATUS_CORROBORATED))
    conn = _Connection()
    result = asyncio.run(ingestion.resolve_organization_name(conn, _Client(), _Client(), "AGP", "different context"))

    assert result == "Aurora Grid Power"
    query, args = conn.executed[0]
    assert "context_sha256" in query
    assert args[0] == "AGP"
    assert len(args[1]) == 64


def test_cached_unverified_name_stays_raw() -> None:
    conn = _Connection({"resolved_organization_name": "Aurora Grid Power", "verification_status_code": STATUS_UNCORROBORATED})
    result = asyncio.run(ingestion.resolve_organization_name(conn, _UnavailableClient(), _Client(), "AGP", "context"))
    assert result == "AGP"


def test_unavailable_and_no_resolution_keep_raw(monkeypatch: pytest.MonkeyPatch) -> None:
    unavailable = _Connection()
    assert asyncio.run(ingestion.resolve_organization_name(unavailable, _UnavailableClient(), _Client(), "AGP", "context")) == "AGP"

    monkeypatch.setattr(ingestion, "resolve_and_verify_organization_name", lambda *_args: None)
    no_resolution = _Connection()
    assert asyncio.run(ingestion.resolve_organization_name(no_resolution, _Client(), _Client(), "AGP", "context")) == "AGP"
    assert no_resolution.executed == []


@pytest.mark.parametrize("status,expected", [(STATUS_CORROBORATED, "Aurora Grid Power"), (STATUS_UNCORROBORATED, "AGP")])
def test_new_resolution_is_persisted_but_only_verified_name_is_returned(
    monkeypatch: pytest.MonkeyPatch, status: str, expected: str
) -> None:
    monkeypatch.setattr(ingestion, "resolve_and_verify_organization_name", lambda *_args: _resolution(status))
    conn = _Connection()
    result = asyncio.run(ingestion.resolve_organization_name(conn, _Client(), _Client(), "AGP", "context"))

    assert result == expected
    assert len(conn.executed) == 1
    assert "organization_name_resolution" in conn.executed[0][0]


def test_verified_resolution_links_to_the_stable_corporate_entity_id() -> None:
    """Persist the catalog identity instead of rejoining by display name."""
    conn = _Connection()

    asyncio.run(
        ingestion.link_verified_organization_entity(
            conn,
            "AGP",
            "context",
            "entity-id",
        )
    )

    query, args = conn.executed[0]
    assert "resolved_corporate_entity_id" in query
    assert "verification_status_code = 'verify_corroborated'" in query
    assert args == ("entity-id", "AGP", ingestion._context_sha256("context"))
