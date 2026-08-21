"""Shared source-post eligibility SQL for reader-facing evidence reads."""

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

# The SQL projection of the fixed ABAC rule in ``main._can_see_post``. Keep
# the authorized-id placeholder explicit so every reader query shares the
# same public-or-affiliated visibility boundary.
SOURCE_POST_VISIBILITY_SQL = (
    "({alias}.visibility_code = 'public' "
    "or {alias}.corporate_entity_id = any({authorized_entity_ids}::uuid[]))"
)


def source_context_present_sql(alias: str) -> str:
    return " or ".join(
        f"nullif(btrim({alias}.{column}), '') is not null" for column in SOURCE_CONTEXT_COLUMNS
    )


def source_context_missing_sql(alias: str) -> str:
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
