from backend.app.post_eligibility import (
    SOURCE_CONTEXT_COLUMNS,
    SOURCE_POST_ELIGIBILITY_SQL,
    SOURCE_POST_VISIBILITY_SQL,
    source_context_missing_sql,
    source_context_present_sql,
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


def test_visibility_sql_is_shared_public_or_affiliated_abac_projection() -> None:
    visibility = SOURCE_POST_VISIBILITY_SQL.format(
        alias="post", authorized_entity_ids="$2"
    )

    assert visibility == (
        "(post.visibility_code = 'public' or "
        "post.corporate_entity_id = any($2::uuid[]))"
    )
