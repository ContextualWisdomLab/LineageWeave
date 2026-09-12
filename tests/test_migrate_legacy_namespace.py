"""Tests for scripts/migrate_legacy_namespace.py (ADR 0157 tooling).

The migration must be deterministic, dry-run by default, refuse unknown
namespaces, and never touch provenance columns. These tests exercise the
pure ``canonicalize_ontology_iri`` mapping and the async scan/rewrite flow against an
in-memory fake connection -- no live PostgreSQL required.
"""

from __future__ import annotations

import ast
import asyncio
import importlib.util
from pathlib import Path

import pytest

MIGRATION_SCRIPT_PATH = (
    Path(__file__).resolve().parents[1] / "scripts" / "migrate_legacy_namespace.py"
)
MIGRATION_MODULE_SPEC = importlib.util.spec_from_file_location(
    "migrate_legacy_namespace",
    MIGRATION_SCRIPT_PATH,
)
migrate_legacy_namespace = importlib.util.module_from_spec(MIGRATION_MODULE_SPEC)
MIGRATION_MODULE_SPEC.loader.exec_module(migrate_legacy_namespace)

CANONICAL_ONTOLOGY_NAMESPACE = migrate_legacy_namespace.CANONICAL_NAMESPACE
LEGACY_ONTOLOGY_NAMESPACE = migrate_legacy_namespace.LEGACY_NAMESPACE


def test_migration_operator_uses_semantic_owned_identifiers() -> None:
    """Keep migration, database, IRI, and command names context-specific."""
    module_source = MIGRATION_SCRIPT_PATH.read_text(encoding="utf-8")
    syntax_tree = ast.parse(module_source)
    owned_identifiers = {
        syntax_node.id
        for syntax_node in ast.walk(syntax_tree)
        if isinstance(syntax_node, ast.Name)
    }
    owned_identifiers.update(
        syntax_node.arg
        for syntax_node in ast.walk(syntax_tree)
        if isinstance(syntax_node, ast.arg)
    )
    owned_identifiers.update(
        syntax_node.name
        for syntax_node in ast.walk(syntax_tree)
        if isinstance(syntax_node, (ast.AsyncFunctionDef, ast.FunctionDef))
    )

    assert owned_identifiers.isdisjoint(
        {
            "apply",
            "args",
            "canonical",
            "canonicalize",
            "change",
            "conn",
            "dsn",
            "iri",
            "migrate",
            "new",
            "parser",
            "planned",
            "row",
            "rows",
            "unexpected",
            "updated",
        }
    )
    assert {
        "apply_changes",
        "canonicalize_ontology_iri",
        "command_arguments",
        "command_parser",
        "database_connection",
        "migrate_legacy_ontology_namespace",
        "ontology_iri",
        "planned_iri_rewrites",
        "source_mention_rows",
        "unexpected_namespace_records",
    } <= owned_identifiers


class TestCanonicalize:
    def test_maps_legacy_to_canonical(self) -> None:
        assert (
            migrate_legacy_namespace.canonicalize_ontology_iri(
                f"{LEGACY_ONTOLOGY_NAMESPACE}Project"
            )
            == f"{CANONICAL_ONTOLOGY_NAMESPACE}Project"
        )

    def test_canonical_rows_are_left_alone(self) -> None:
        ontology_iri = f"{CANONICAL_ONTOLOGY_NAMESPACE}Person"
        assert migrate_legacy_namespace.canonicalize_ontology_iri(ontology_iri) is None

    def test_unknown_namespaces_return_none(self) -> None:
        assert (
            migrate_legacy_namespace.canonicalize_ontology_iri(
                "https://example.com/other#Thing"
            )
            is None
        )

    def test_fragment_is_preserved_exactly(self) -> None:
        ontology_term = "CorporateEntity"
        mapped_ontology_iri = migrate_legacy_namespace.canonicalize_ontology_iri(
            f"{LEGACY_ONTOLOGY_NAMESPACE}{ontology_term}"
        )
        assert mapped_ontology_iri == f"{CANONICAL_ONTOLOGY_NAMESPACE}{ontology_term}"
        assert mapped_ontology_iri.endswith(ontology_term)


class FakeRecord:
    def __init__(self, post_id: str, project_name: str, ontology_iri: str):
        self._record_values = {
            "post_id": post_id,
            "project_name": project_name,
            "ontology_iri": ontology_iri,
        }

    def __getitem__(self, record_field: str):
        return self._record_values[record_field]


@pytest.fixture()
def _patch_connect(monkeypatch: pytest.MonkeyPatch):
    """Route asyncpg.connect to a factory over a caller-supplied connection."""
    connection_factory_state: dict = {}

    def _connection_factory(database_connection):
        def connect_database(target_dsn):
            assert "postgresql://" in target_dsn
            return _AsyncReturn(database_connection)

        connection_factory_state["database_connection"] = database_connection
        return connect_database

    connection_factory_state["connection_factory"] = _connection_factory
    yield connection_factory_state


class _AsyncReturn:
    """Awaitable that resolves immediately."""

    def __init__(self, awaited_value):
        self._awaited_value = awaited_value

    def __await__(self):
        if False:
            yield
        return self._awaited_value


class FakeConnection:
    """Minimal asyncpg surface: one select, transactional updates."""

    def __init__(self, mention_rows: list[FakeRecord]):
        self.mention_rows = mention_rows
        self.executed_updates: list[tuple] = []
        self.transaction_entered = False

    async def fetch(self, query: str):
        assert "post_project_mention" in query
        return self.mention_rows

    def transaction(self):
        return self

    async def __aenter__(self):
        self.transaction_entered = True
        return self

    async def __aexit__(self, *exc_info):
        return False

    async def execute(self, query: str, *args):
        assert "update post_project_mention" in query
        self.executed_updates.append(args)
        return "UPDATE 1"

    async def close(self):
        pass


def test_dry_run_reports_without_writing(
    capsys: pytest.CaptureFixture[str], _patch_connect, monkeypatch: pytest.MonkeyPatch
) -> None:
    source_mention_rows = [
        FakeRecord("p1", "Alpha", f"{LEGACY_ONTOLOGY_NAMESPACE}Project"),
        FakeRecord("p2", "Beta", f"{CANONICAL_ONTOLOGY_NAMESPACE}Team"),
    ]
    database_connection = FakeConnection(source_mention_rows)
    monkeypatch.setattr(
        migrate_legacy_namespace.asyncpg,
        "connect",
        _patch_connect["connection_factory"](database_connection),
    )
    exit_code = asyncio.run(
        migrate_legacy_namespace.migrate_legacy_ontology_namespace(
            "postgresql://unused",
            apply_changes=False,
        )
    )

    assert exit_code == 0
    captured_output = capsys.readouterr().out
    assert "dry run" in captured_output
    assert (
        f"{LEGACY_ONTOLOGY_NAMESPACE}Project -> {CANONICAL_ONTOLOGY_NAMESPACE}Project"
    ) in captured_output
    assert database_connection.executed_updates == []
    assert not database_connection.transaction_entered


def test_apply_rewrites_only_legacy_rows(
    _patch_connect, monkeypatch: pytest.MonkeyPatch
) -> None:
    source_mention_rows = [
        FakeRecord("p1", "Alpha", f"{LEGACY_ONTOLOGY_NAMESPACE}Project"),
        FakeRecord("p2", "Beta", f"{CANONICAL_ONTOLOGY_NAMESPACE}Team"),
    ]
    database_connection = FakeConnection(source_mention_rows)
    monkeypatch.setattr(
        migrate_legacy_namespace.asyncpg,
        "connect",
        _patch_connect["connection_factory"](database_connection),
    )
    exit_code = asyncio.run(
        migrate_legacy_namespace.migrate_legacy_ontology_namespace(
            "postgresql://unused",
            apply_changes=True,
        )
    )

    assert exit_code == 0
    assert len(database_connection.executed_updates) == 1
    source_post_id, project_name, canonical_iri, legacy_iri = (
        database_connection.executed_updates[0]
    )
    assert (source_post_id, project_name) == ("p1", "Alpha")
    assert canonical_iri == f"{CANONICAL_ONTOLOGY_NAMESPACE}Project"
    assert legacy_iri == f"{LEGACY_ONTOLOGY_NAMESPACE}Project"


def test_unknown_namespace_fails_closed(
    capsys: pytest.CaptureFixture[str], _patch_connect, monkeypatch: pytest.MonkeyPatch
) -> None:
    source_mention_rows = [FakeRecord("p3", "Gamma", "https://example.com/weird#X")]
    database_connection = FakeConnection(source_mention_rows)
    monkeypatch.setattr(
        migrate_legacy_namespace.asyncpg,
        "connect",
        _patch_connect["connection_factory"](database_connection),
    )
    exit_code = asyncio.run(
        migrate_legacy_namespace.migrate_legacy_ontology_namespace(
            "postgresql://unused",
            apply_changes=False,
        )
    )

    assert exit_code == 1
    captured_output = capsys.readouterr().out
    assert "UNEXPECTED" in captured_output
    assert "nothing written" in captured_output
    assert database_connection.executed_updates == []


def test_clean_database_is_a_no_op(
    capsys: pytest.CaptureFixture[str], _patch_connect, monkeypatch: pytest.MonkeyPatch
) -> None:
    source_mention_rows = [
        FakeRecord("p4", "Delta", f"{CANONICAL_ONTOLOGY_NAMESPACE}Post")
    ]
    database_connection = FakeConnection(source_mention_rows)
    monkeypatch.setattr(
        migrate_legacy_namespace.asyncpg,
        "connect",
        _patch_connect["connection_factory"](database_connection),
    )
    exit_code = asyncio.run(
        migrate_legacy_namespace.migrate_legacy_ontology_namespace(
            "postgresql://unused",
            apply_changes=True,
        )
    )

    assert exit_code == 0
    captured_output = capsys.readouterr().out
    assert "no legacy namespace rows remain" in captured_output
    assert database_connection.executed_updates == []
