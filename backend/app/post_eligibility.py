"""Shared source-post eligibility and visibility contracts."""

from collections.abc import Collection, Mapping
from typing import Any

SOURCE_CONTEXT_COLUMNS = (
    "source_author_code",
    "source_author_name",
    "source_company_code",
    "source_company_name",
    "source_process_unit_code",
    "source_process_unit_name",
    "source_sales_pool_code",
    "source_sales_pool_name",
    "source_customer_code",
    "source_customer_name",
    "source_project_code",
    "source_project_name",
)


def source_context_present_sql(alias: str) -> str:
    """SQL fragment: true if any source-context column on `alias` is non-blank."""
    return " or ".join(
        f"nullif(btrim({alias}.{column}), '') is not null" for column in SOURCE_CONTEXT_COLUMNS
    )


def source_context_missing_sql(alias: str) -> str:
    """SQL fragment: true if every source-context column on `alias` is blank."""
    return " and ".join(
        f"nullif(btrim({alias}.{column}), '') is null" for column in SOURCE_CONTEXT_COLUMNS
    )


SOURCE_POST_ELIGIBILITY_SQL = (
    "nullif(btrim({alias}.source_draft_code), '') is null "
    "and nullif(btrim({alias}.source_deleted_flag), '') is null "
    "and not ("
    "({missing_context}) "
    "and exists ("
    "select 1 from source_post real_post "
    "where ({present_context})"
    ")"
    ")"
).format(
    alias="{alias}",
    missing_context=source_context_missing_sql("{alias}"),
    present_context=source_context_present_sql("real_post"),
)


def source_post_scope_sql(alias: str) -> str:
    """Return the shared ABAC SQL using entity ``$1`` and process-unit ``$2``."""
    return (
        f"({alias}.visibility_code = 'public' or "
        f"({alias}.corporate_entity_id::text = any($1::text[]) and "
        f"(cardinality($2::text[]) = 0 or "
        f"{alias}.process_unit_id::text = any($2::text[]))))"
    )


def source_post_visible(
    post: Mapping[str, object],
    corporate_entity_ids: Collection[str],
    process_unit_ids: Collection[str],
) -> bool:
    """Apply the same public-or-bound-scope ABAC contract outside SQL."""
    if post["visibility_code"] == "public":
        return True
    return str(post["corporate_entity_id"]) in corporate_entity_ids and (
        not process_unit_ids or str(post["process_unit_id"]) in process_unit_ids
    )


async def fetch_visible_eligible_source_post_ids_for_share(
    conn: Any,
    corporate_entity_ids: Collection[str],
    process_unit_ids: Collection[str],
    source_post_ids: Collection[str],
) -> frozenset[str]:
    """Lock and return captured sources still visible and buyer-eligible.

    This repository operation owns the SQL-level authorization boundary so
    replay consumers do not copy ABAC/eligibility SQL. The query is deliberately
    literal at the asyncpg sink; request identities remain bind parameters.
    """
    if not source_post_ids:
        return frozenset()
    rows = await conn.fetch(
        "select source_post.post_id::text as post_id from source_post where source_post.post_id = any($3::uuid[]) and (source_post.visibility_code = 'public' or (source_post.corporate_entity_id::text = any($1::text[]) and (cardinality($2::text[]) = 0 or source_post.process_unit_id::text = any($2::text[])))) and nullif(btrim(source_post.source_draft_code), '') is null and nullif(btrim(source_post.source_deleted_flag), '') is null and not ((nullif(btrim(source_post.source_author_code), '') is null and nullif(btrim(source_post.source_author_name), '') is null and nullif(btrim(source_post.source_company_code), '') is null and nullif(btrim(source_post.source_company_name), '') is null and nullif(btrim(source_post.source_process_unit_code), '') is null and nullif(btrim(source_post.source_process_unit_name), '') is null and nullif(btrim(source_post.source_sales_pool_code), '') is null and nullif(btrim(source_post.source_sales_pool_name), '') is null and nullif(btrim(source_post.source_customer_code), '') is null and nullif(btrim(source_post.source_customer_name), '') is null and nullif(btrim(source_post.source_project_code), '') is null and nullif(btrim(source_post.source_project_name), '') is null) and exists (select 1 from source_post real_post where (nullif(btrim(real_post.source_author_code), '') is not null or nullif(btrim(real_post.source_author_name), '') is not null or nullif(btrim(real_post.source_company_code), '') is not null or nullif(btrim(real_post.source_company_name), '') is not null or nullif(btrim(real_post.source_process_unit_code), '') is not null or nullif(btrim(real_post.source_process_unit_name), '') is not null or nullif(btrim(real_post.source_sales_pool_code), '') is not null or nullif(btrim(real_post.source_sales_pool_name), '') is not null or nullif(btrim(real_post.source_customer_code), '') is not null or nullif(btrim(real_post.source_customer_name), '') is not null or nullif(btrim(real_post.source_project_code), '') is not null or nullif(btrim(real_post.source_project_name), '') is not null))) order by source_post.post_id for share",
        sorted(corporate_entity_ids),
        sorted(process_unit_ids),
        sorted(set(source_post_ids)),
    )
    return frozenset(str(row["post_id"]) for row in rows)
