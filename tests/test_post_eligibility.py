import asyncio

from backend.app.auth import CurrentAccount
from backend.app.main import _can_see_post
from backend.app.post_eligibility import (
    SOURCE_CONTEXT_COLUMNS,
    SOURCE_POST_ELIGIBILITY_SQL,
    fetch_visible_customer_hint_evidence,
    lock_visible_customer_hint_sources,
    source_context_missing_sql,
    source_context_present_sql,
    source_post_scope_sql,
)


class _QueryCapture:
    """Record SQL submitted by the source-post eligibility repository boundary."""

    def __init__(self) -> None:
        """Initialize an empty ordered query ledger."""
        self.queries: list[str] = []

    async def fetch(self, query: str, *_args: object) -> list[object]:
        """Capture one query without emulating PostgreSQL result rows."""
        self.queries.append(query)
        return []


def _account(*, process_unit_ids: frozenset[str]) -> CurrentAccount:
    return CurrentAccount(
        user_account_id="account-a",
        external_subject_id="subject-a",
        display_name="Synthetic Member",
        preferred_locale="en",
        corporate_entity_ids=frozenset({"entity-a"}),
        process_unit_ids=process_unit_ids,
        permission_codes=frozenset({"post_read"}),
    )


def _normalize_sql(statement: str) -> str:
    """Normalize insignificant layout around SQL predicates for contract comparison."""
    normalized = " ".join(statement.lower().split())
    return normalized.replace("( ", "(").replace(" )", ")")


def test_keyverse_private_post_requires_the_bound_process_unit() -> None:
    account = _account(process_unit_ids=frozenset({"process-a"}))
    assert _can_see_post(
        account,
        {"visibility_code": "private", "corporate_entity_id": "entity-a", "process_unit_id": "process-a"},
    )
    assert not _can_see_post(
        account,
        {"visibility_code": "private", "corporate_entity_id": "entity-a", "process_unit_id": "process-b"},
    )
    assert not _can_see_post(
        account,
        {"visibility_code": "private", "corporate_entity_id": "entity-a", "process_unit_id": None},
    )


def test_local_identity_retains_existing_corporate_scope() -> None:
    assert _can_see_post(
        _account(process_unit_ids=frozenset()),
        {"visibility_code": "private", "corporate_entity_id": "entity-a", "process_unit_id": None},
    )


def test_real_source_context_hides_pure_seed_rows_at_read_boundary() -> None:
    eligibility = SOURCE_POST_ELIGIBILITY_SQL.format(alias="post")

    assert "source_draft_code" in eligibility
    assert "source_deleted_flag" in eligibility
    assert "not ((" in eligibility
    assert "exists (select 1 from source_post real_post" in eligibility
    for column in SOURCE_CONTEXT_COLUMNS:
        assert f"post.{column}" in source_context_missing_sql("post")
        assert f"real_post.{column}" in source_context_present_sql("real_post")


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
