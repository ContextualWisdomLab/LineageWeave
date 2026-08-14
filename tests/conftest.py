"""Keep PostgreSQL integration tests out of the operator's runtime database."""

from __future__ import annotations

import os
from urllib.parse import urlsplit, urlunsplit

import psycopg
from psycopg import sql


_BASE_DSN = os.environ.get("LINEAGEWEAVE_TEST_DSN", "postgresql://localhost/postgres")
_MANAGED_DATABASE = "" if "LINEAGEWEAVE_TEST_DSN" in os.environ else f"lineageweave_test_{os.getpid()}"


def _database_dsn(dsn: str, database_name: str) -> str:
    """Select an exact per-process database without changing connection credentials."""
    parsed = urlsplit(dsn)
    return urlunsplit((parsed.scheme, parsed.netloc, f"/{database_name}", parsed.query, parsed.fragment))


def pytest_configure() -> None:
    """Create a process-local database unless the caller supplied an explicit test DSN."""
    if not _MANAGED_DATABASE:
        return
    with psycopg.connect(_BASE_DSN, autocommit=True) as connection:
        connection.execute(
            sql.SQL("DROP DATABASE IF EXISTS {} WITH (FORCE)").format(
                sql.Identifier(_MANAGED_DATABASE)
            )
        )
        connection.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(_MANAGED_DATABASE)))
    os.environ["LINEAGEWEAVE_TEST_DSN"] = _database_dsn(_BASE_DSN, _MANAGED_DATABASE)


def pytest_unconfigure() -> None:
    """Drop only the exact process-local test database created by this session."""
    if not _MANAGED_DATABASE:
        return
    with psycopg.connect(_BASE_DSN, autocommit=True) as connection:
        connection.execute(
            sql.SQL("DROP DATABASE IF EXISTS {} WITH (FORCE)").format(
                sql.Identifier(_MANAGED_DATABASE)
            )
        )
