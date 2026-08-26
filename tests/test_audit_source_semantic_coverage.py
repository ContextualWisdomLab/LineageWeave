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


@pytest.mark.parametrize(
    "value",
    ["document_key; select secret", 'document_key" from private_table --'],
)
def test_key_coverage_rejects_sql_syntax_in_identifiers(value: str) -> None:
    with pytest.raises(ValueError, match="invalid PostgreSQL identifier"):
        asyncio.run(
            audit_source_semantic_coverage(
                "postgresql://synthetic",
                "source_schema.source_rows",
                {},
                source_key=value,
                coverage_table="semantic_schema.document_nodes",
                coverage_key="document_key",
            )
        )


def test_audit_reports_distinct_semantic_key_coverage(monkeypatch) -> None:
    """Coverage compares normalized keys and emits counts, never source values."""
    class Connection:
        calls = 0

        async def fetchrow(self, query: str):
            self.calls += 1
            if self.calls == 1:
                return {"row_count": 3}
            assert 'from "source_schema"."source_rows"' in query
            assert 'from "semantic_schema"."document_nodes"' in query
            assert 'full join coverage_keys using (key_value)' in query
            return {
                "source_key_count": 2,
                "coverage_key_count": 2,
                "matched_key_count": 2,
                "source_without_coverage_count": 0,
                "coverage_without_source_count": 0,
            }

        async def close(self) -> None:
            pass

    async def connect(_dsn: str):
        return Connection()

    monkeypatch.setattr("scripts.audit_source_semantic_coverage.asyncpg.connect", connect)

    result = asyncio.run(
        audit_source_semantic_coverage(
            "postgresql://synthetic",
            "source_schema.source_rows",
            {},
            source_key="document_key",
            coverage_table="semantic_schema.document_nodes",
            coverage_key="document_key",
        )
    )

    assert result["semantic_key_coverage"] == {
        "source_key_count": 2,
        "coverage_key_count": 2,
        "matched_key_count": 2,
        "source_without_coverage_count": 0,
        "coverage_without_source_count": 0,
    }


def test_audit_requires_complete_key_coverage_configuration() -> None:
    with pytest.raises(ValueError, match="all required"):
        asyncio.run(
            audit_source_semantic_coverage(
                "postgresql://synthetic",
                "source_schema.source_rows",
                {},
                source_key="document_key",
            )
        )


def test_audit_reports_assertion_evidence_and_prov_schema_without_values(
    monkeypatch,
) -> None:
    """Assertion evidence stays aggregate and PROV deployment is exact."""

    class Connection:
        calls = 0

        async def fetchrow(self, query: str):
            self.calls += 1
            if self.calls == 1:
                return {"row_count": 2}
            assert 'from "semantic_schema"."edge_assertions"' in query
            return {
                "assertion_count": 9,
                "observed_count": 6,
                "observed_without_evidence_count": 0,
                "inferred_count": 2,
                "inferred_without_direct_evidence_count": 1,
                "predicted_count": 1,
                "predicted_without_direct_evidence_count": 1,
                "ungoverned_status_count": 0,
            }

        async def fetch(self, query: str, schema: str, required: list[str]):
            assert "information_schema.tables" in query
            assert schema == "semantic_schema"
            return [{"table_name": name} for name in required]

        async def close(self) -> None:
            pass

    async def connect(_dsn: str):
        return Connection()

    monkeypatch.setattr("scripts.audit_source_semantic_coverage.asyncpg.connect", connect)

    result = asyncio.run(
        audit_source_semantic_coverage(
            "postgresql://synthetic",
            "source_schema.source_rows",
            {},
            assertion_table="semantic_schema.edge_assertions",
            assertion_status="evidence_status",
            assertion_evidence="evidence_id",
            provenance_schema="semantic_schema",
        )
    )

    assert result["semantic_assertion_evidence"] == {
        "assertion_count": 9,
        "observed_count": 6,
        "observed_without_evidence_count": 0,
        "inferred_count": 2,
        "inferred_without_direct_evidence_count": 1,
        "predicted_count": 1,
        "predicted_without_direct_evidence_count": 1,
        "ungoverned_status_count": 0,
        "source_evidence_boundary_complete": True,
    }
    assert result["normalized_provenance_schema"] == {
        "required_table_count": 13,
        "present_table_count": 13,
        "complete": True,
    }


def test_audit_requires_complete_assertion_configuration() -> None:
    with pytest.raises(ValueError, match="assertion_table.*all required"):
        asyncio.run(
            audit_source_semantic_coverage(
                "postgresql://synthetic",
                "source_schema.source_rows",
                {},
                assertion_table="semantic_schema.edge_assertions",
            )
        )
