import asyncio
from contextlib import asynccontextmanager

import pytest
from fastapi import HTTPException

from backend.app.auth import CurrentAccount
from backend.app.main import _load_visible_post

from backend.app.post_eligibility import (
    SOURCE_CONTEXT_COLUMNS,
    SOURCE_POST_ELIGIBILITY_SQL,
    normalize_source_detail_state_code,
    SOURCE_POST_VISIBILITY_SQL,
    source_context_missing_sql,
    source_context_present_sql,
)


class _VisiblePostConnection:
    """Return one synthetic W row while preserving the real helper path."""

    def __init__(self, row: dict[str, object]) -> None:
        self.row = row

    async def fetchrow(self, *_args: object) -> dict[str, object]:
        """Return the fixture row for the loader's bound query."""
        return self.row


class _VisiblePostPool:
    """Minimal asyncpg-pool seam for the visibility boundary test."""

    def __init__(self, row: dict[str, object]) -> None:
        self.connection = _VisiblePostConnection(row)

    @asynccontextmanager
    async def acquire(self):
        """Yield the fake connection through the same async context protocol."""
        yield self.connection


def test_author_bookmark_can_read_w_post_but_analysis_default_rejects() -> None:
    """Bookmark visibility may opt into an authorized W row without weakening analysis."""
    row = {
        "post_id": "post-w",
        "post_title": "Synthetic draft",
        "voc_type_code": "other",
        "visibility_code": "public",
        "corporate_entity_id": "entity-1",
        "source_detail_state_code": " W ",
        "created_at": None,
        "author_account_id": "account-1",
        "source_process_unit_code": None,
        "source_author_code": None,
        "source_company_code": None,
        "source_customer_code": None,
        "source_project_code": None,
        "source_sales_pool_code": None,
        "corporate_entity_code": None,
    }
    account = CurrentAccount(
        user_account_id="account-1",
        external_subject_id="subject-1",
        display_name="Anonymous user",
        preferred_locale="en",
        corporate_entity_ids=frozenset({"entity-1"}),
        permission_codes=frozenset({"post_read"}),
    )
    pool = _VisiblePostPool(row)

    assert asyncio.run(_load_visible_post("post-w", account, pool, allow_writing=True)) == row
    with pytest.raises(HTTPException) as raised:
        asyncio.run(_load_visible_post("post-w", account, pool))
    assert raised.value.status_code == 422


def test_real_source_context_hides_pure_seed_rows_at_read_boundary() -> None:
    eligibility = SOURCE_POST_ELIGIBILITY_SQL.format(alias="post")

    assert "source_draft_code" in eligibility
    assert "source_deleted_flag" in eligibility
    assert "not ((" in eligibility
    assert "exists (select 1 from source_post real_post" in eligibility
    for column in SOURCE_CONTEXT_COLUMNS:
        assert f"post.{column}" in source_context_missing_sql("post")
        assert f"real_post.{column}" in source_context_present_sql("real_post")


def test_source_detail_state_normalization_removes_transport_padding() -> None:
    """Reader filters and W authorization use one canonical state value."""
    assert normalize_source_detail_state_code("  W ") == "W"
    assert normalize_source_detail_state_code("  D ") == "D"
    assert normalize_source_detail_state_code(" d ") == "D"
    assert normalize_source_detail_state_code("   ") is None
    assert normalize_source_detail_state_code(None) is None


def test_writing_state_visibility_normalizes_padded_codes() -> None:
    from backend.app.post_eligibility import source_post_state_visibility_sql

    visibility = source_post_state_visibility_sql(
        "post", corporate_param=1, account_param=2, admin_param=3
    )

    assert "upper(btrim(post.source_detail_state_code))" in visibility
    assert "<> 'W'" in visibility


def test_visibility_sql_is_shared_public_or_affiliated_abac_projection() -> None:
    visibility = SOURCE_POST_VISIBILITY_SQL.format(
        alias="post", authorized_entity_ids="$2"
    )

    assert visibility == (
        "(post.visibility_code = 'public' or "
        "post.corporate_entity_id = any($2::uuid[]))"
    )
