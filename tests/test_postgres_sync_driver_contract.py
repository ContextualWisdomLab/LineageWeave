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
    _translated_error,
    connection_kwargs_from_dsn,
    errors,
    sql,
)


_REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
_FORBIDDEN_IMPORT = re.compile(r"(?m)^\s*(?:import\s+psycopg2\b|from\s+psycopg2\b)")


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


def test_generated_identifier_quoting_is_postgresql_safe() -> None:
    """Generated database and role names stay identifiers, never SQL text."""
    statement = sql.SQL("create database {}").format(sql.Identifier('tenant"archive'))
    assert statement == 'create database "tenant""archive"'


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


def test_unknown_dsn_query_option_fails_closed() -> None:
    """A connection option must never disappear merely because drivers differ."""
    with pytest.raises(ValueError, match="unsupported PostgreSQL DSN option"):
        connection_kwargs_from_dsn(
            "postgresql://alice:secret@db.example/archive?target_session_attrs=read-write"
        )


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
