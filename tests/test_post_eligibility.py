from backend.app.post_eligibility import (
    SOURCE_CONTEXT_COLUMNS,
    SOURCE_POST_ELIGIBILITY_SQL,
    source_context_missing_sql,
    source_context_present_sql,
)
from backend.app.auth import CurrentAccount
from backend.app.main import _can_see_post, _can_see_product_relation_target


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


def test_product_relation_target_requires_its_evidence_scope() -> None:
    """A visible relation cannot disclose a target derived from hidden evidence."""
    account = _account(process_unit_ids=frozenset({"process-a"}))
    assert _can_see_product_relation_target(
        account,
        {
            "target_visibility_code": "private",
            "target_corporate_entity_id": "entity-a",
            "target_process_unit_id": "process-a",
        },
    )
    assert not _can_see_product_relation_target(
        account,
        {
            "target_visibility_code": "private",
            "target_corporate_entity_id": "entity-a",
            "target_process_unit_id": "process-b",
        },
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
