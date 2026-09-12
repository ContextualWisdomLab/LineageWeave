from __future__ import annotations

import ast
from pathlib import Path

import pytest

from backend.app.post_chat_replay_policy import PostChatAuthorizationScope


def test_restricted_generation_scope_allows_only_equal_or_broader_reader() -> None:
    """Reject a reader whose corporate or process scope is narrower than generation."""
    captured = PostChatAuthorizationScope.captured(
        corporate_entity_ids={"corp-a"},
        process_unit_ids={"pu-a"},
    )

    assert captured.is_subsumed_by(
        current_corporate_entity_ids={"corp-a"},
        current_process_unit_ids={"pu-a", "pu-b"},
    )
    assert captured.is_subsumed_by(
        current_corporate_entity_ids={"corp-a"},
        current_process_unit_ids=set(),
    )
    assert not captured.is_subsumed_by(
        current_corporate_entity_ids={"corp-a"},
        current_process_unit_ids={"pu-b"},
    )
    assert not captured.is_subsumed_by(
        current_corporate_entity_ids={"corp-b"},
        current_process_unit_ids=set(),
    )


def test_unrestricted_generation_process_scope_rejects_later_restriction() -> None:
    """Preserve the authenticated empty-set meaning as unrestricted process scope."""
    captured = PostChatAuthorizationScope.captured(
        corporate_entity_ids={"corp-a"},
        process_unit_ids=set(),
    )

    assert captured.process_scope_limited is False
    assert captured.is_subsumed_by(
        current_corporate_entity_ids={"corp-a", "corp-b"},
        current_process_unit_ids=set(),
    )
    assert not captured.is_subsumed_by(
        current_corporate_entity_ids={"corp-a"},
        current_process_unit_ids={"pu-a"},
    )


def test_scope_identity_values_are_normalized_to_strings() -> None:
    """Normalize heterogeneous identity values before scope comparison or persistence."""
    captured = PostChatAuthorizationScope.captured(
        corporate_entity_ids={1, "2"},
        process_unit_ids={3},
    )

    assert captured.corporate_entity_ids == frozenset({"1", "2"})
    assert captured.process_unit_ids == frozenset({"3"})


def test_inconsistent_process_scope_receipt_is_rejected() -> None:
    """Fail closed when persisted limited/unrestricted metadata contradicts child rows."""
    with pytest.raises(ValueError, match="process_scope_limited"):
        PostChatAuthorizationScope(
            corporate_entity_ids=frozenset({"corp-a"}),
            process_unit_ids=frozenset(),
            process_scope_limited=True,
        )

    with pytest.raises(ValueError, match="process_scope_limited"):
        PostChatAuthorizationScope(
            corporate_entity_ids=frozenset({"corp-a"}),
            process_unit_ids=frozenset({"pu-a"}),
            process_scope_limited=False,
        )


def test_migration_models_receipt_scope_sources_and_reverse_dependency_order() -> None:
    """Keep normalized replay evidence and rollback dependency order executable."""
    forward = Path("migrations/0249_post_chat_authorization_scope.sql").read_text()
    rollback = Path("migrations/rollback/0249_post_chat_authorization_scope.sql").read_text()

    assert "post_chat_authorization_receipt" in forward
    assert "process_scope_limited boolean not null" in forward
    assert "post_chat_corporate_entity_scope" in forward
    assert "post_chat_process_unit_scope" in forward
    assert "post_chat_source" in forward
    assert "unique (post_id, question_norm, source_post_id)" in forward
    assert "references post_chat_authorization_receipt" in forward
    assert rollback.index("drop table if exists post_chat_source") < rollback.index(
        "drop table if exists post_chat_authorization_receipt"
    )


def test_source_deletion_invalidates_answers_that_used_the_source() -> None:
    """Require source deletion to atomically invalidate derived replay state."""
    forward = Path("migrations/0249_post_chat_authorization_scope.sql").read_text().lower()
    rollback = Path("migrations/rollback/0249_post_chat_authorization_scope.sql").read_text().lower()

    assert "invalidate_post_chat_replay_on_source_post_delete" in forward
    assert "before delete on source_post" in forward
    assert "delete from post_chat_result" in forward
    assert "source_post_id = old.post_id" in forward
    assert "drop trigger if exists invalidate_post_chat_replay_on_source_delete" in rollback
    assert "drop function if exists invalidate_post_chat_replay_on_source_post_delete" in rollback


def test_application_boundary_consumes_receipt_validated_replay_policy() -> None:
    """Require the replay consumer to delegate source authorization to its owner boundary."""
    main_source = Path("backend/app/main.py").read_text()
    ingestion_source = Path("backend/app/post_chat_ingestion.py").read_text()
    eligibility_source = Path("backend/app/post_eligibility.py").read_text()

    assert "PostChatAuthorizationScope" in ingestion_source
    assert "post_chat_authorization_receipt" in ingestion_source
    assert "fetch_visible_eligible_source_post_ids_for_share" in ingestion_source
    assert "source_post_scope_sql" in eligibility_source
    assert "SOURCE_POST_ELIGIBILITY_SQL" in eligibility_source
    assert "account.corporate_entity_ids" in main_source
    assert "account.process_unit_ids" in main_source


@pytest.mark.parametrize(
    ("path", "minimum_calls"),
    [
        ("backend/app/main.py", 2),
        ("tests/test_post_chat_ingestion.py", 1),
    ],
)
def test_replay_scope_factory_calls_keep_keyword_identity_contract(
    path: str,
    minimum_calls: int,
) -> None:
    """Pin keyword-only scope construction at both endpoint and regression-test boundaries."""
    tree = ast.parse(Path(path).read_text())
    scope_calls = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "captured"
        and isinstance(node.func.value, ast.Name)
        and node.func.value.id == "PostChatAuthorizationScope"
    ]

    assert len(scope_calls) >= minimum_calls
    for call in scope_calls:
        assert call.args == []
        assert {keyword.arg for keyword in call.keywords} == {
            "corporate_entity_ids",
            "process_unit_ids",
        }
