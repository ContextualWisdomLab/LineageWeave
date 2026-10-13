"""The literal customer evidence sinks stay aligned with shared authorization SQL."""
import asyncio
from backend.app.post_eligibility import (fetch_visible_customer_hint_evidence, lock_visible_customer_hint_sources, source_post_scope_sql, SOURCE_POST_ELIGIBILITY_SQL)

class _QueryCapture:
    """Record SQL submitted by the source-post eligibility repository boundary."""

    def __init__(self) -> None:
        """Initialize an empty ordered query ledger."""
        self.queries: list[str] = []

    async def fetch(self, query: str, *_args: object) -> list[object]:
        """Capture one query without emulating PostgreSQL result rows."""
        self.queries.append(query)
        return []


def _normalize_sql(statement: str) -> str:
    """Normalize insignificant layout around SQL predicates for contract comparison."""
    normalized = " ".join(statement.lower().split())
    return normalized.replace("( ", "(").replace(" )", ")")



def test_customer_hint_queries_match_shared_scope_and_eligibility_contracts() -> None:
    """Both literal hint queries must remain equivalent to the canonical ABAC predicates."""
    connection = _QueryCapture()

    asyncio.run(
        fetch_visible_customer_hint_evidence(
            connection,  # type: ignore[arg-type]
            ["entity-a"],
            ["process-a"],
            "customer-a",
        )
    )
    asyncio.run(
        lock_visible_customer_hint_sources(
            connection,  # type: ignore[arg-type]
            ["entity-a"],
            ["process-a"],
            "customer-a",
            ["post-a"],
        )
    )

    expected_scope = _normalize_sql(source_post_scope_sql("source_post"))
    expected_eligibility = _normalize_sql(SOURCE_POST_ELIGIBILITY_SQL.format(alias="source_post"))
    assert len(connection.queries) == 2
    for query in connection.queries:
        normalized_query = _normalize_sql(query)
        assert expected_scope in normalized_query
        assert expected_eligibility in normalized_query