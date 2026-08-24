from __future__ import annotations

import asyncio
from types import SimpleNamespace

import pytest

import backend.app.organization_name_resolution_ingestion as ingestion
from lineageweave.relation_verification import (
    STATUS_CORROBORATED,
    STATUS_UNCORROBORATED,
)
from lineageweave.corporate_hierarchy_resolution import OrganizationNameAlias


class _Connection:
    def __init__(self, cached: dict[str, str] | None = None) -> None:
        self.cached = cached
        self.executed: list[tuple[str, tuple[object, ...]]] = []
        self.alias_rows: list[dict[str, str]] = []

    async def fetchrow(self, _query: str, _raw_name: str):
        return self.cached

    async def fetch(self, query: str, *_args: object):
        assert "organization_name_resolution" in query
        return list(self.alias_rows)

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


def test_prepared_name_resolution_defers_cache_write_until_apply(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        ingestion,
        "resolve_and_verify_organization_name",
        lambda *_args: _resolution(STATUS_CORROBORATED),
    )
    conn = _Connection()

    prepared = asyncio.run(
        ingestion.prepare_organization_name_resolution(
            conn,
            _Client(),
            _Client(),
            "AGP",
            "context",
        )
    )

    assert prepared.resolved_name == "Aurora Grid Power"
    assert conn.executed == []
    assert (
        asyncio.run(
            ingestion.apply_prepared_organization_name_resolution(conn, prepared)
        )
        == "Aurora Grid Power"
    )
    assert len(conn.executed) == 1


def test_load_corroborated_aliases_skips_stub_connections() -> None:
    assert asyncio.run(ingestion.load_corroborated_organization_name_aliases(object())) == []


def test_load_corroborated_aliases_returns_search_verified_pairs() -> None:
    conn = _Connection()
    conn.alias_rows = [
        {
            "raw_organization_name": "AGP",
            "resolved_organization_name": "Aurora Grid Power",
        }
    ]
    aliases = asyncio.run(ingestion.load_corroborated_organization_name_aliases(conn))
    assert aliases == [
        OrganizationNameAlias(alt_label="AGP", pref_label="Aurora Grid Power")
    ]
