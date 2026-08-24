"""Tests for scripts/migrate_legacy_namespace.py (ADR 0157 tooling).

The migration must be deterministic, dry-run by default, refuse unknown
namespaces, and never touch provenance columns. These tests exercise the
pure ``canonicalize`` mapping and the async scan/rewrite flow against an
in-memory fake connection -- no live PostgreSQL required.
"""

from __future__ import annotations

import asyncio
import importlib.util
from pathlib import Path

import pytest

_SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "migrate_legacy_namespace.py"
_spec = importlib.util.spec_from_file_location("migrate_legacy_namespace", _SCRIPT)
migrate_legacy_namespace = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(migrate_legacy_namespace)

CANONICAL = migrate_legacy_namespace.CANONICAL_NAMESPACE
LEGACY = migrate_legacy_namespace.LEGACY_NAMESPACE


class TestCanonicalize:
    def test_maps_legacy_to_canonical(self) -> None:
        assert migrate_legacy_namespace.canonicalize(f"{LEGACY}Project") == f"{CANONICAL}Project"

    def test_canonical_rows_are_left_alone(self) -> None:
        iri = f"{CANONICAL}Person"
        assert migrate_legacy_namespace.canonicalize(iri) is None

    def test_unknown_namespaces_return_none(self) -> None:
        assert migrate_legacy_namespace.canonicalize("https://example.com/other#Thing") is None

    def test_fragment_is_preserved_exactly(self) -> None:
        term = "CorporateEntity"
        mapped = migrate_legacy_namespace.canonicalize(f"{LEGACY}{term}")
        assert mapped == f"{CANONICAL}{term}"
        assert mapped.endswith(term)


class FakeRecord:
    def __init__(self, post_id: str, project_name: str, ontology_iri: str):
        self._data = {
            "post_id": post_id,
            "project_name": project_name,
            "ontology_iri": ontology_iri,
        }

    def __getitem__(self, key: str):
        return self._data[key]


@pytest.fixture()
def _patch_connect(monkeypatch: pytest.MonkeyPatch):
    """Route asyncpg.connect to a factory over a caller-supplied connection."""
    holder: dict = {}

    def _factory(conn):
        def _connect(dsn):
            assert "postgresql://" in dsn
            return _AsyncReturn(conn)
        holder["conn"] = conn
        return _connect

    holder["factory"] = _factory
    yield holder


class _AsyncReturn:
    """Awaitable that resolves immediately."""

    def __init__(self, value):
        self._value = value

    def __await__(self):
        if False:
            yield
        return self._value


class FakeConnection:
    """Minimal asyncpg surface: one select, transactional updates."""

    def __init__(self, rows: list[FakeRecord]):
        self.rows = rows
        self.updates: list[tuple] = []
        self.transaction_entered = False

    async def fetch(self, query: str):
        assert "post_project_mention" in query
        return self.rows

    def transaction(self):
        return self

    async def __aenter__(self):
        self.transaction_entered = True
        return self

    async def __aexit__(self, *exc_info):
        return False

    async def execute(self, query: str, *args):
        assert "update post_project_mention" in query
        self.updates.append(args)
        return "UPDATE 1"

    async def close(self):
        pass


def test_dry_run_reports_without_writing(capsys: pytest.CaptureFixture[str], _patch_connect, monkeypatch: pytest.MonkeyPatch) -> None:
    rows = [
        FakeRecord("p1", "Alpha", f"{LEGACY}Project"),
        FakeRecord("p2", "Beta", f"{CANONICAL}Team"),
    ]
    conn = FakeConnection(rows)
    monkeypatch.setattr(migrate_legacy_namespace.asyncpg, "connect", _patch_connect["factory"](conn))
    rc = asyncio.run(migrate_legacy_namespace.migrate("postgresql://unused", apply=False))

    assert rc == 0
    out = capsys.readouterr().out
    assert "dry run" in out
    assert f"{LEGACY}Project -> {CANONICAL}Project" in out
    assert conn.updates == []
    assert not conn.transaction_entered


def test_apply_rewrites_only_legacy_rows(_patch_connect, monkeypatch: pytest.MonkeyPatch) -> None:
    rows = [
        FakeRecord("p1", "Alpha", f"{LEGACY}Project"),
        FakeRecord("p2", "Beta", f"{CANONICAL}Team"),
    ]
    conn = FakeConnection(rows)
    monkeypatch.setattr(migrate_legacy_namespace.asyncpg, "connect", _patch_connect["factory"](conn))
    rc = asyncio.run(migrate_legacy_namespace.migrate("postgresql://unused", apply=True))

    assert rc == 0
    assert len(conn.updates) == 1
    post_id, project_name, new_iri, old_iri = conn.updates[0]
    assert (post_id, project_name) == ("p1", "Alpha")
    assert new_iri == f"{CANONICAL}Project"
    assert old_iri == f"{LEGACY}Project"


def test_unknown_namespace_fails_closed(capsys: pytest.CaptureFixture[str], _patch_connect, monkeypatch: pytest.MonkeyPatch) -> None:
    rows = [FakeRecord("p3", "Gamma", "https://example.com/weird#X")]
    conn = FakeConnection(rows)
    monkeypatch.setattr(migrate_legacy_namespace.asyncpg, "connect", _patch_connect["factory"](conn))
    rc = asyncio.run(migrate_legacy_namespace.migrate("postgresql://unused", apply=False))

    assert rc == 1
    out = capsys.readouterr().out
    assert "UNEXPECTED" in out
    assert "nothing written" in out
    assert conn.updates == []


def test_clean_database_is_a_no_op(capsys: pytest.CaptureFixture[str], _patch_connect, monkeypatch: pytest.MonkeyPatch) -> None:
    rows = [FakeRecord("p4", "Delta", f"{CANONICAL}Post")]
    conn = FakeConnection(rows)
    monkeypatch.setattr(migrate_legacy_namespace.asyncpg, "connect", _patch_connect["factory"](conn))
    rc = asyncio.run(migrate_legacy_namespace.migrate("postgresql://unused", apply=True))

    assert rc == 0
    out = capsys.readouterr().out
    assert "no legacy namespace rows remain" in out
    assert conn.updates == []
