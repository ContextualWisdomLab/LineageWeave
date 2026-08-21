from backend.app.post_eligibility import (
    SOURCE_CONTEXT_COLUMNS,
    SOURCE_POST_ELIGIBILITY_SQL,
    normalize_source_detail_state_code,
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


def test_source_detail_state_normalization_removes_transport_padding() -> None:
    """Reader filters and W authorization use one canonical state value."""
    assert normalize_source_detail_state_code("  W ") == "W"
    assert normalize_source_detail_state_code("  D ") == "D"
    assert normalize_source_detail_state_code("   ") is None
    assert normalize_source_detail_state_code(None) is None
