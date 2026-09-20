"""Regression contracts for synchronous PostgreSQL review findings."""

from __future__ import annotations

import re
from pathlib import Path

import pg8000.dbapi as _dbapi
import pytest

from lineageweave.postgres_sync import Connection, errors


_ROOT = Path(__file__).resolve().parents[1]
_WORKFLOW = _ROOT / ".github" / "workflows" / "tests.yml"


def test_lock_candidate_artifact_is_unique_per_workflow_attempt_and_review_durable() -> None:
    """Resolver evidence must survive review and never collide across rerun attempts."""
    workflow = _WORKFLOW.read_text(encoding="utf-8")

    assert "uv-lock-candidate-${{ github.sha }}-${{ github.run_attempt }}" in workflow
    retention_match = re.search(
        r"name: uv-lock-candidate-\$\{\{ github\.sha \}\}-\$\{\{ github\.run_attempt \}\}"
        r"[\s\S]*?retention-days:\s*(\d+)",
        workflow,
    )
    assert retention_match is not None
    assert int(retention_match.group(1)) >= 7


@pytest.mark.parametrize(
    ("method_name", "sqlstate", "expected_type"),
    (
        ("commit", "23505", errors.UniqueViolation),
        ("rollback", "23503", errors.ForeignKeyViolation),
    ),
)
def test_connection_transaction_methods_translate_database_errors(
    method_name: str,
    sqlstate: str,
    expected_type: type[BaseException],
) -> None:
    """Commit and rollback retain SQLSTATE-specific compatibility at the adapter boundary."""

    class NativeConnection:
        autocommit = False

        def commit(self) -> None:
            raise _dbapi.DatabaseError({"C": sqlstate, "M": "synthetic transaction failure"})

        def rollback(self) -> None:
            raise _dbapi.DatabaseError({"C": sqlstate, "M": "synthetic transaction failure"})

    connection = Connection(NativeConnection(), database="archive")

    with pytest.raises(expected_type):
        getattr(connection, method_name)()


def test_connection_context_uses_translating_transaction_methods() -> None:
    """Context-manager completion must not bypass transaction error translation."""

    class NativeConnection:
        autocommit = False

        def commit(self) -> None:
            raise _dbapi.DatabaseError({"C": "23505", "M": "deferred unique violation"})

        def rollback(self) -> None:
            raise _dbapi.DatabaseError({"C": "23503", "M": "deferred foreign-key violation"})

    connection = Connection(NativeConnection(), database="archive")

    with pytest.raises(errors.UniqueViolation):
        with connection:
            pass

    with pytest.raises(errors.ForeignKeyViolation):
        with connection:
            raise RuntimeError("force rollback")
