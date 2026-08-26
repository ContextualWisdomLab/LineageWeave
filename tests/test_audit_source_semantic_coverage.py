import asyncio

import pytest

from scripts.audit_source_semantic_coverage import (
    _identifier,
    audit_source_semantic_coverage,
)


def test_audit_returns_aggregate_roles_without_source_values(monkeypatch) -> None:
    class Connection:
        closed = False

        async def fetchrow(self, query: str):
            assert 'from "source_schema"."source_rows"' in query
            assert '"body_text"' in query
            return {"row_count": 3, "body_nonblank_count": 2}

        async def close(self) -> None:
            self.closed = True

    connection = Connection()

    async def connect(_dsn: str):
        return connection

    monkeypatch.setattr("scripts.audit_source_semantic_coverage.asyncpg.connect", connect)

    result = asyncio.run(
        audit_source_semantic_coverage(
            "postgresql://synthetic",
            "source_schema.source_rows",
            {"body": "body_text"},
        )
    )

    assert result == {
        "row_count": 3,
        "semantic_role_nonblank_counts": {"body": 2},
    }
    assert connection.closed


def test_audit_rejects_sql_syntax_in_identifiers() -> None:
    with pytest.raises(ValueError, match="invalid PostgreSQL identifier"):
        _identifier('source_rows; select secret')
