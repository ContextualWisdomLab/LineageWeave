"""Shared source-post eligibility SQL for reader-facing evidence reads."""

WRITING_SOURCE_DETAIL_STATE_CODE = "W"


def normalize_source_detail_state_code(value: object) -> str | None:
    """Return a canonical, case-insensitive source detail state code."""
    if not isinstance(value, str):
        return None
    normalized = value.strip().upper()
    return normalized or None


def source_post_state_visibility_sql(
    alias: str, *, corporate_param: int, account_param: int, admin_param: int
) -> str:
    """Apply public/corp visibility, with an author/admin exception for W."""
    return (
        f"((coalesce(upper(btrim({alias}.source_detail_state_code)), '') = "
        f"'{WRITING_SOURCE_DETAIL_STATE_CODE}' "
        f"and ({alias}.author_account_id = ${account_param}::uuid "
        f"or ${admin_param}::boolean)) "
        f"or (coalesce(upper(btrim({alias}.source_detail_state_code)), '') <> "
        f"'{WRITING_SOURCE_DETAIL_STATE_CODE}' and ({alias}.visibility_code = 'public' "
        f"or {alias}.corporate_entity_id::text = any(${corporate_param}::text[]))))"
    )

SOURCE_CONTEXT_COLUMNS = (
    "source_system_code",
    "source_record_key",
    "source_author_code",
    "source_author_name",
    "source_company_code",
    "source_company_name",
    "source_process_unit_code",
    "source_process_unit_name",
    "source_stage_code",
    "source_detail_state_code",
    "source_sales_pool_code",
    "source_sales_pool_name",
    "source_order_pool_code",
    "source_sales_order_code",
    "source_inspection_point_code",
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
    """Build SQL that detects any nonblank source-context field on an alias."""
    return " or ".join(
        [
            *(f"nullif(btrim({alias}.{column}), '') is not null" for column in SOURCE_CONTEXT_COLUMNS),
            f"{alias}.source_sales_order_item_number is not null",
        ]
    )


def source_context_missing_sql(alias: str) -> str:
    """Build SQL that requires every source-context field on an alias to be blank."""
    return " and ".join(
        [
            *(f"nullif(btrim({alias}.{column}), '') is null" for column in SOURCE_CONTEXT_COLUMNS),
            f"{alias}.source_sales_order_item_number is null",
        ]
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
    "and coalesce(upper(btrim({alias}.source_detail_state_code)), '') <> 'W'"
)
