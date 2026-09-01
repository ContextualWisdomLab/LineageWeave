"""Commercial-license and compatibility contract for synchronous PostgreSQL tooling.

LineageWeave's runtime uses asyncpg, but seed/admin/schema tooling still needs a
small synchronous DB-API boundary. This contract prevents that boundary from
silently reintroducing the former psycopg2-binary dependency and locks the
behaviour that generated database/role identifiers, PostgreSQL DSNs, and
constraint/security assertions rely on.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from lineageweave.postgres_sync import (
    DatabaseError,
    OperationalError,
    _translated_error,
    connect,
    connection_kwargs_from_dsn,
    errors,
    sql,
)


_REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
_FORBIDDEN_IMPORT = re.compile(r"(?m)^\s*(?:import\s+psycopg2\b|from\s+psycopg2\b)")
_UPLOAD_ARTIFACT_SHA = "043fb46d1a93c77aae656e7c1c64a875d1fc6a0a"


def test_sync_postgres_driver_is_not_psycopg2() -> None:
    """Executable Python and dependency metadata must not retain psycopg2."""
    roots = (
        _REPOSITORY_ROOT / "lineageweave",
        _REPOSITORY_ROOT / "scripts",
        _REPOSITORY_ROOT / "tests",
        _REPOSITORY_ROOT / "backend",
    )
    offenders: list[str] = []
    for root in roots:
        for path in root.rglob("*.py"):
            if path == Path(__file__):
                continue
            if _FORBIDDEN_IMPORT.search(path.read_text(encoding="utf-8")):
                offenders.append(str(path.relative_to(_REPOSITORY_ROOT)))

    pyproject = (_REPOSITORY_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    assert "psycopg2-binary" not in pyproject
    assert "pg8000" in pyproject
    assert offenders == []


def test_lockfile_matches_synchronous_postgres_driver_contract() -> None:
    """The reproducible environment must resolve the same driver as pyproject."""
    lockfile = (_REPOSITORY_ROOT / "uv.lock").read_text(encoding="utf-8")
    assert 'name = "psycopg2"' not in lockfile
    assert 'name = "psycopg2-binary"' not in lockfile
    assert 'name = "pg8000"' in lockfile


def test_ci_preserves_resolver_output_when_committed_lock_is_stale() -> None:
    """A stale frozen lock must fail closed while preserving the resolver candidate."""
    workflow = (_REPOSITORY_ROOT / ".github" / "workflows" / "tests.yml").read_text(
        encoding="utf-8"
    )

    lock_check = workflow.index("uv lock --check")
    frozen_sync = workflow.index("uv sync --frozen --extra dev --extra backend")
    assert lock_check < frozen_sync
    assert f"actions/upload-artifact@{_UPLOAD_ARTIFACT_SHA}" in workflow
    assert "uv-lock-candidate-${{ github.sha }}" in workflow
    assert "if-no-files-found: error" in workflow


def test_generated_identifier_quoting_is_postgresql_safe() -> None:
    """Generated database and role names stay identifiers, never SQL text."""
    statement = sql.SQL("create database {}").format(sql.Identifier('tenant"archive'))
    assert statement == 'create database "tenant""archive"'


def test_generated_sql_rejects_raw_interpolation() -> None:
    """Dynamic SQL fragments must use an explicit safe composable wrapper."""
    with pytest.raises(TypeError, match="SQL interpolation requires"):
        sql.SQL("create database {}").format('tenant"; drop database archive; --')


def test_dsn_query_options_are_mapped_without_silent_loss() -> None:
    """Supported libpq-style DSN options survive the pg8000 adapter boundary."""
    kwargs = connection_kwargs_from_dsn(
        "postgresql://alice:p%40ss@db.example:6543/archive"
        "?connect_timeout=7&application_name=lineageweave-test&sslmode=disable"
    )

    assert kwargs["user"] == "alice"
    assert kwargs["password"] == "p@ss"
    assert kwargs["host"] == "db.example"
    assert kwargs["port"] == 6543
    assert kwargs["database"] == "archive"
    assert kwargs["timeout"] == 7.0
    assert kwargs["application_name"] == "lineageweave-test"
    assert kwargs["ssl_context"] is False


def test_dsn_without_user_preserves_libpq_os_user_default(monkeypatch) -> None:
    """Existing admin DSNs without a username still use the local OS account."""
    monkeypatch.setattr("lineageweave.postgres_sync.getpass.getuser", lambda: "ci-runner")

    kwargs = connection_kwargs_from_dsn("postgresql://localhost/postgres")

    assert kwargs["user"] == "ci-runner"
    assert kwargs["host"] == "localhost"
    assert kwargs["database"] == "postgres"


def test_unknown_dsn_query_option_fails_closed() -> None:
    """A connection option must never disappear merely because drivers differ."""
    with pytest.raises(ValueError, match="unsupported PostgreSQL DSN option"):
        connection_kwargs_from_dsn(
            "postgresql://alice:secret@db.example/archive?target_session_attrs=read-write"
        )


def test_dsn_fragment_fails_closed_instead_of_being_silently_discarded() -> None:
    """URI fragments are outside libpq's connection grammar and must not disappear."""
    with pytest.raises(ValueError, match="must not include a fragment"):
        connection_kwargs_from_dsn(
            "postgresql://alice:secret@db.example/archive#sslmode=require"
        )


def test_duplicate_dsn_query_option_fails_closed() -> None:
    """Conflicting duplicate options must not be collapsed by query parsing."""
    with pytest.raises(ValueError, match="duplicate PostgreSQL DSN option: sslmode"):
        connection_kwargs_from_dsn(
            "postgresql://alice:secret@db.example/archive?sslmode=require&sslmode=disable"
        )


def test_connect_translates_server_startup_failure_to_operational_error(monkeypatch) -> None:
    """Server-side startup refusal must preserve the old reachability-probe contract."""
    failure = DatabaseError({"C": "28P01", "M": "password authentication failed"})

    def fail_connect(**_: object) -> None:
        raise failure

    monkeypatch.setattr("lineageweave.postgres_sync._dbapi.connect", fail_connect)

    with pytest.raises(OperationalError) as raised:
        connect("postgresql://alice:secret@db.example/archive")

    assert raised.value.args == failure.args
    assert raised.value.__cause__ is failure


@pytest.mark.parametrize(
    ("sqlstate", "expected_type"),
    (
        ("23502", errors.NotNullViolation),
        ("23505", errors.UniqueViolation),
        ("23514", errors.CheckViolation),
        ("23P01", errors.ExclusionViolation),
        ("42501", errors.InsufficientPrivilege),
        ("P0001", errors.RaiseException),
    ),
)
def test_schema_fixture_sqlstates_keep_typed_error_contract(
    sqlstate: str,
    expected_type: type[BaseException],
) -> None:
    """Migrated tests still distinguish integrity, privilege, and trigger failures."""
    translated = _translated_error(DatabaseError({"C": sqlstate, "M": "synthetic"}))
    assert isinstance(translated, expected_type)
