"""Shared source-post eligibility and visibility contracts."""

from collections.abc import Collection, Mapping, Sequence
from typing import Any

import asyncpg

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


async def fetch_visible_customer_hint_evidence(
    database_connection: asyncpg.Connection,
    corporate_entity_ids: Sequence[str],
    process_unit_ids: Sequence[str],
    hint_code: str,
) -> list[asyncpg.Record]:
    """Load at most five eligible hint posts after applying caller ABAC.

    Title/body are selected only after the corporate/process predicate is
    satisfied, so a guessed foreign hint cannot disclose foreign evidence to
    the resolver. This query lives with the shared source-post authorization
    boundary rather than in the Customer Master consumer.
    """
    return await database_connection.fetch(
        """
        select source_post.post_id,
               source_post.post_title,
               left(source_post.post_body, 20000) as post_body,
               encode(sha256(convert_to(jsonb_build_array(source_post.post_title, source_post.post_body)::text, 'UTF8')), 'hex') as source_content_digest
          from source_post
         where btrim(source_post.source_customer_code) = $3
           and (
               source_post.visibility_code = 'public'
               or (
                   source_post.corporate_entity_id::text = any($1::text[])
                   and (
                       cardinality($2::text[]) = 0
                       or source_post.process_unit_id::text = any($2::text[])
                   )
               )
           )
           and nullif(btrim(source_post.source_draft_code), '') is null
           and nullif(btrim(source_post.source_deleted_flag), '') is null
           and not (
               (
                   nullif(btrim(source_post.source_author_code), '') is null
                   and nullif(btrim(source_post.source_author_name), '') is null
                   and nullif(btrim(source_post.source_company_code), '') is null
                   and nullif(btrim(source_post.source_company_name), '') is null
                   and nullif(btrim(source_post.source_process_unit_code), '') is null
                   and nullif(btrim(source_post.source_process_unit_name), '') is null
                   and nullif(btrim(source_post.source_sales_pool_code), '') is null
                   and nullif(btrim(source_post.source_sales_pool_name), '') is null
                   and nullif(btrim(source_post.source_customer_code), '') is null
                   and nullif(btrim(source_post.source_customer_name), '') is null
                   and nullif(btrim(source_post.source_project_code), '') is null
                   and nullif(btrim(source_post.source_project_name), '') is null
               )
               and exists (
                   select 1
                     from source_post real_post
                    where (
                        nullif(btrim(real_post.source_author_code), '') is not null
                        or nullif(btrim(real_post.source_author_name), '') is not null
                        or nullif(btrim(real_post.source_company_code), '') is not null
                        or nullif(btrim(real_post.source_company_name), '') is not null
                        or nullif(btrim(real_post.source_process_unit_code), '') is not null
                        or nullif(btrim(real_post.source_process_unit_name), '') is not null
                        or nullif(btrim(real_post.source_sales_pool_code), '') is not null
                        or nullif(btrim(real_post.source_sales_pool_name), '') is not null
                        or nullif(btrim(real_post.source_customer_code), '') is not null
                        or nullif(btrim(real_post.source_customer_name), '') is not null
                        or nullif(btrim(real_post.source_project_code), '') is not null
                        or nullif(btrim(real_post.source_project_name), '') is not null
                    )
               )
           )
         order by source_post.created_at desc, source_post.post_id desc
         limit 5
        """,
        list(corporate_entity_ids),
        list(process_unit_ids),
        hint_code,
    )


async def lock_visible_customer_hint_sources(
    database_connection: asyncpg.Connection,
    corporate_entity_ids: Sequence[str],
    process_unit_ids: Sequence[str],
    hint_code: str,
    post_ids: Sequence[str],
) -> list[asyncpg.Record]:
    """Revalidate and share-lock the captured hint sources before persistence."""
    return await database_connection.fetch(
        """
        select source_post.post_id,
               encode(sha256(convert_to(jsonb_build_array(source_post.post_title, source_post.post_body)::text, 'UTF8')), 'hex') as source_content_digest
          from source_post
         where source_post.post_id::text = any($4::text[])
           and btrim(source_post.source_customer_code) = $3
           and (
               source_post.visibility_code = 'public'
               or (
                   source_post.corporate_entity_id::text = any($1::text[])
                   and (
                       cardinality($2::text[]) = 0
                       or source_post.process_unit_id::text = any($2::text[])
                   )
               )
           )
           and nullif(btrim(source_post.source_draft_code), '') is null
           and nullif(btrim(source_post.source_deleted_flag), '') is null
           and not (
               (
                   nullif(btrim(source_post.source_author_code), '') is null
                   and nullif(btrim(source_post.source_author_name), '') is null
                   and nullif(btrim(source_post.source_company_code), '') is null
                   and nullif(btrim(source_post.source_company_name), '') is null
                   and nullif(btrim(source_post.source_process_unit_code), '') is null
                   and nullif(btrim(source_post.source_process_unit_name), '') is null
                   and nullif(btrim(source_post.source_sales_pool_code), '') is null
                   and nullif(btrim(source_post.source_sales_pool_name), '') is null
                   and nullif(btrim(source_post.source_customer_code), '') is null
                   and nullif(btrim(source_post.source_customer_name), '') is null
                   and nullif(btrim(source_post.source_project_code), '') is null
                   and nullif(btrim(source_post.source_project_name), '') is null
               )
               and exists (
                   select 1
                     from source_post real_post
                    where (
                        nullif(btrim(real_post.source_author_code), '') is not null
                        or nullif(btrim(real_post.source_author_name), '') is not null
                        or nullif(btrim(real_post.source_company_code), '') is not null
                        or nullif(btrim(real_post.source_company_name), '') is not null
                        or nullif(btrim(real_post.source_process_unit_code), '') is not null
                        or nullif(btrim(real_post.source_process_unit_name), '') is not null
                        or nullif(btrim(real_post.source_sales_pool_code), '') is not null
                        or nullif(btrim(real_post.source_sales_pool_name), '') is not null
                        or nullif(btrim(real_post.source_customer_code), '') is not null
                        or nullif(btrim(real_post.source_customer_name), '') is not null
                        or nullif(btrim(real_post.source_project_code), '') is not null
                        or nullif(btrim(real_post.source_project_name), '') is not null
                    )
               )
           )
         order by source_post.post_id
         for share
        """,
        list(corporate_entity_ids),
        list(process_unit_ids),
        hint_code,
        list(post_ids),
    )


async def fetch_eligible_summary_access_metadata(
    conn: asyncpg.Connection, post_id: str,
) -> dict[str, Any] | None:
    """Classify initial denial without loading an unauthorized title or body.

    Preserve the existing summary 403 contract for eligible foreign sources;
    missing or lifecycle-ineligible sources remain 404. This projection is
    diagnostic authorization metadata, never model evidence or buyer output.
    """
    row = await conn.fetchrow(
        """
        select source_post.visibility_code, source_post.corporate_entity_id,
               source_post.process_unit_id
          from source_post
         where source_post.post_id = $1::uuid
           and nullif(btrim(source_post.source_draft_code), '') is null
           and nullif(btrim(source_post.source_deleted_flag), '') is null
           and not (
               (
                   nullif(btrim(source_post.source_author_code), '') is null
                   and nullif(btrim(source_post.source_author_name), '') is null
                   and nullif(btrim(source_post.source_company_code), '') is null
                   and nullif(btrim(source_post.source_company_name), '') is null
                   and nullif(btrim(source_post.source_process_unit_code), '') is null
                   and nullif(btrim(source_post.source_process_unit_name), '') is null
                   and nullif(btrim(source_post.source_sales_pool_code), '') is null
                   and nullif(btrim(source_post.source_sales_pool_name), '') is null
                   and nullif(btrim(source_post.source_customer_code), '') is null
                   and nullif(btrim(source_post.source_customer_name), '') is null
                   and nullif(btrim(source_post.source_project_code), '') is null
                   and nullif(btrim(source_post.source_project_name), '') is null
               )
               and exists (
                   select 1
                     from source_post real_post
                    where (
                        nullif(btrim(real_post.source_author_code), '') is not null
                        or nullif(btrim(real_post.source_author_name), '') is not null
                        or nullif(btrim(real_post.source_company_code), '') is not null
                        or nullif(btrim(real_post.source_company_name), '') is not null
                        or nullif(btrim(real_post.source_process_unit_code), '') is not null
                        or nullif(btrim(real_post.source_process_unit_name), '') is not null
                        or nullif(btrim(real_post.source_sales_pool_code), '') is not null
                        or nullif(btrim(real_post.source_sales_pool_name), '') is not null
                        or nullif(btrim(real_post.source_customer_code), '') is not null
                        or nullif(btrim(real_post.source_customer_name), '') is not null
                        or nullif(btrim(real_post.source_project_code), '') is not null
                        or nullif(btrim(real_post.source_project_name), '') is not null
                    )
               )
           )
        """,
        post_id,
    )
    return None if row is None else dict(row)


async def capture_visible_summary_source(
    conn: asyncpg.Connection,
    corporate_entity_ids: Collection[str],
    process_unit_ids: Collection[str],
    post_id: str,
) -> dict[str, Any] | None:
    """Capture one scoped eligible summary source under a caller-owned share lock.

    The full body/title and digest come from the same source row; callers must
    release this short transaction before normalization or external inference.
    """
    row = await conn.fetchrow(
        """
        select source_post.*,
               customer.corporate_entity_code,
               encode(sha256(convert_to(jsonb_build_array(source_post.post_title, source_post.post_body)::text, 'UTF8')), 'hex') as source_content_digest
          from source_post
          left join corporate_entity customer
            on customer.corporate_entity_id = source_post.corporate_entity_id
         where source_post.post_id = $3::uuid
           and (source_post.visibility_code = 'public' or (source_post.corporate_entity_id::text = any($1::text[]) and (cardinality($2::text[]) = 0 or source_post.process_unit_id::text = any($2::text[]))))
           and nullif(btrim(source_post.source_draft_code), '') is null
           and nullif(btrim(source_post.source_deleted_flag), '') is null
           and not (
               (
                   nullif(btrim(source_post.source_author_code), '') is null
                   and nullif(btrim(source_post.source_author_name), '') is null
                   and nullif(btrim(source_post.source_company_code), '') is null
                   and nullif(btrim(source_post.source_company_name), '') is null
                   and nullif(btrim(source_post.source_process_unit_code), '') is null
                   and nullif(btrim(source_post.source_process_unit_name), '') is null
                   and nullif(btrim(source_post.source_sales_pool_code), '') is null
                   and nullif(btrim(source_post.source_sales_pool_name), '') is null
                   and nullif(btrim(source_post.source_customer_code), '') is null
                   and nullif(btrim(source_post.source_customer_name), '') is null
                   and nullif(btrim(source_post.source_project_code), '') is null
                   and nullif(btrim(source_post.source_project_name), '') is null
               )
               and exists (
                   select 1
                     from source_post real_post
                    where (
                        nullif(btrim(real_post.source_author_code), '') is not null
                        or nullif(btrim(real_post.source_author_name), '') is not null
                        or nullif(btrim(real_post.source_company_code), '') is not null
                        or nullif(btrim(real_post.source_company_name), '') is not null
                        or nullif(btrim(real_post.source_process_unit_code), '') is not null
                        or nullif(btrim(real_post.source_process_unit_name), '') is not null
                        or nullif(btrim(real_post.source_sales_pool_code), '') is not null
                        or nullif(btrim(real_post.source_sales_pool_name), '') is not null
                        or nullif(btrim(real_post.source_customer_code), '') is not null
                        or nullif(btrim(real_post.source_customer_name), '') is not null
                        or nullif(btrim(real_post.source_project_code), '') is not null
                        or nullif(btrim(real_post.source_project_name), '') is not null
                    )
               )
           )
         for share of source_post
        """,
        sorted(corporate_entity_ids),
        sorted(process_unit_ids),
        post_id,
    )
    return None if row is None else dict(row)


async def lock_unchanged_summary_source(
    conn: asyncpg.Connection,
    corporate_entity_ids: Collection[str],
    process_unit_ids: Collection[str],
    captured: Mapping[str, object],
) -> bool:
    """Reauthorize identity, eligibility, scope and captured content before use."""
    current = await capture_visible_summary_source(
        conn, corporate_entity_ids, process_unit_ids, str(captured["post_id"])
    )
    return current is not None and current == dict(captured)
