"""Shared source-post eligibility SQL for reader-facing evidence reads."""

WRITING_SOURCE_DETAIL_STATE_CODE = "W"


def source_post_state_visibility_sql(
    alias: str, *, corporate_param: int, account_param: int, admin_param: int
) -> str:
    """Apply public/corp visibility, with an author/admin exception for W."""
    return (
        f"(({alias}.source_detail_state_code = '{WRITING_SOURCE_DETAIL_STATE_CODE}' "
        f"and ({alias}.author_account_id = ${account_param}::uuid "
        f"or ${admin_param}::boolean)) "
        f"or ({alias}.source_detail_state_code is distinct from "
        f"'{WRITING_SOURCE_DETAIL_STATE_CODE}' and ({alias}.visibility_code = 'public' "
        f"or {alias}.corporate_entity_id::text = any(${corporate_param}::text[]))))"
    )

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
    return " or ".join(
        f"nullif(btrim({alias}.{column}), '') is not null" for column in SOURCE_CONTEXT_COLUMNS
    )


def source_context_missing_sql(alias: str) -> str:
    return " and ".join(
        f"nullif(btrim({alias}.{column}), '') is null" for column in SOURCE_CONTEXT_COLUMNS
    )


SOURCE_POST_READER_ELIGIBILITY_SQL = (
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

# Derived readers (ontology, lineage, ranking, reports, Ask, and content
# projections) must never consume a writing-in-progress source. Raw board
# list/detail routes opt into SOURCE_POST_READER_ELIGIBILITY_SQL explicitly.
SOURCE_POST_ELIGIBILITY_SQL = (
    f"({SOURCE_POST_READER_ELIGIBILITY_SQL}) "
    "and coalesce(btrim({alias}.source_detail_state_code), '') <> 'W'"
)
