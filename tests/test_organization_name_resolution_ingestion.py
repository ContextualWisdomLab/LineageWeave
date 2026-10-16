from __future__ import annotations

import asyncio
from types import SimpleNamespace

import pytest

import backend.app.organization_name_resolution_ingestion as ingestion
from lineageweave.corporate_hierarchy_resolution import (
    OrganizationNameAlias as CorporateHierarchyOrganizationNameAlias,
)
from lineageweave.organization_alias import OrganizationNameAlias
from lineageweave.relation_verification import STATUS_CORROBORATED, STATUS_UNCORROBORATED


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
        CorporateHierarchyOrganizationNameAlias(
            alt_label="AGP", pref_label="Aurora Grid Power"
        )
    ]


class _AliasConnection:
    def __init__(self, rows: list[dict[str, str | None]]) -> None:
        self.rows = rows
        self.bound_status: object | None = None
        self.query = ""

    async def fetch(self, query: str, status: object):
        self.query = query
        self.bound_status = status
        return self.rows


def test_fetch_corroborated_aliases_binds_verified_status() -> None:
    conn = _AliasConnection(
        [
            {
                "raw_organization_name": "DC",
                "resolved_organization_name": "Demo Corp",
                "corporate_entity_id": "demo-id",
            }
        ]
    )
    aliases = asyncio.run(ingestion.fetch_corroborated_organization_aliases(conn))
    assert conn.bound_status == STATUS_CORROBORATED
    assert aliases == (
        OrganizationNameAlias(
            alt_label="DC", pref_label="Demo Corp", corporate_entity_id="demo-id"
        ),
    )
    assert "count(distinct entity.corporate_entity_id) = 1" in conn.query
    assert aliases == (OrganizationNameAlias("DC", "Demo Corp", "demo-id"),)


def test_fetch_corroborated_aliases_keeps_catalog_ties_unbound() -> None:
    conn = _AliasConnection(
        [
            {
                "raw_organization_name": "DC",
                "resolved_organization_name": "Demo Corp",
                "corporate_entity_id": None,
            }
        ]
    )
    aliases = asyncio.run(ingestion.fetch_corroborated_organization_aliases(conn))
    assert aliases == (OrganizationNameAlias("DC", "Demo Corp", None),)


class _BoundedAliasConnection:
    def __init__(self) -> None:
        self.query = ""
        self.args: tuple[object, ...] = ()

    async def fetch(self, query: str, *args: object):
        self.query = query
        self.args = args
        return []


def test_fetch_corroborated_aliases_bounds_rows_before_catalog_join() -> None:
    conn = _BoundedAliasConnection()

    aliases = asyncio.run(
        ingestion.fetch_corroborated_organization_aliases(
            conn,
            organization_names=(" Demo Co ", "Demo Corp", "Demo Co"),
        )
    )

    assert aliases == ()
    assert conn.args == (STATUS_CORROBORATED, ["Demo Co", "Demo Corp"])
    lowered = conn.query.lower()
    assert "raw_organization_name = any($2::text[])" in lowered
    assert "resolved_organization_name = any($2::text[])" in lowered
