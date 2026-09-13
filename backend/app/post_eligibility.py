"""Shared source-post eligibility and visibility contracts."""

from collections.abc import Collection, Mapping, Sequence

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
        select post_id, post_title, left(post_body, 20000) as post_body
          from source_post
         where source_customer_code = $3
           and (
               visibility_code = 'public'
               or (
                   corporate_entity_id::text = any($1::text[])
                   and (
                       cardinality($2::text[]) = 0
                       or process_unit_id::text = any($2::text[])
                   )
               )
           )
           and nullif(btrim(source_draft_code), '') is null
           and nullif(btrim(source_deleted_flag), '') is null
           and not (
               (
                   nullif(btrim(source_author_code), '') is null
                   and nullif(btrim(source_author_name), '') is null
                   and nullif(btrim(source_company_code), '') is null
                   and nullif(btrim(source_company_name), '') is null
                   and nullif(btrim(source_process_unit_code), '') is null
                   and nullif(btrim(source_process_unit_name), '') is null
                   and nullif(btrim(source_sales_pool_code), '') is null
                   and nullif(btrim(source_sales_pool_name), '') is null
                   and nullif(btrim(source_customer_code), '') is null
                   and nullif(btrim(source_customer_name), '') is null
                   and nullif(btrim(source_project_code), '') is null
                   and nullif(btrim(source_project_name), '') is null
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
         order by created_at desc, post_id desc
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
        select post_id
          from source_post
         where post_id::text = any($4::text[])
           and source_customer_code = $3
           and (
               visibility_code = 'public'
               or (
                   corporate_entity_id::text = any($1::text[])
                   and (
                       cardinality($2::text[]) = 0
                       or process_unit_id::text = any($2::text[])
                   )
               )
           )
           and nullif(btrim(source_draft_code), '') is null
           and nullif(btrim(source_deleted_flag), '') is null
           and not (
               (
                   nullif(btrim(source_author_code), '') is null
                   and nullif(btrim(source_author_name), '') is null
                   and nullif(btrim(source_company_code), '') is null
                   and nullif(btrim(source_company_name), '') is null
                   and nullif(btrim(source_process_unit_code), '') is null
                   and nullif(btrim(source_process_unit_name), '') is null
                   and nullif(btrim(source_sales_pool_code), '') is null
                   and nullif(btrim(source_sales_pool_name), '') is null
                   and nullif(btrim(source_customer_code), '') is null
                   and nullif(btrim(source_customer_name), '') is null
                   and nullif(btrim(source_project_code), '') is null
                   and nullif(btrim(source_project_name), '') is null
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
         order by post_id
         for share
        """,
        list(corporate_entity_ids),
        list(process_unit_ids),
        hint_code,
        list(post_ids),
    )
