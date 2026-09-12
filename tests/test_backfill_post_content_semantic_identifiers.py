"""Naming and boundary contracts for the synchronous post-content backfill."""

from __future__ import annotations

import ast
from pathlib import Path

SCRIPT_PATH = Path("scripts/backfill_post_content.py")


def test_post_content_backfill_uses_semantic_owned_identifiers() -> None:
    """Keep command, database, record, image, and result names specific."""
    script_source = SCRIPT_PATH.read_text(encoding="utf-8")
    syntax_tree = ast.parse(script_source)
    owned_identifiers = {
        syntax_node.id
        for syntax_node in ast.walk(syntax_tree)
        if isinstance(syntax_node, ast.Name)
    }
    owned_identifiers.update(
        syntax_node.arg
        for syntax_node in ast.walk(syntax_tree)
        if isinstance(syntax_node, ast.arg)
    )
    owned_identifiers.update(
        syntax_node.name
        for syntax_node in ast.walk(syntax_tree)
        if isinstance(syntax_node, (ast.AsyncFunctionDef, ast.FunctionDef))
    )

    assert owned_identifiers.isdisjoint(
        {
            "_parser",
            "args",
            "conn",
            "item",
            "limit",
            "parser",
            "result",
            "row",
            "rows",
        }
    )
    assert {
        "_post_content_backfill_parser",
        "argument_parser",
        "backfill_summary",
        "command_arguments",
        "database_connection",
        "described_image_count",
        "image_result",
        "normalized_post_content",
        "post_limit",
        "selected_post_record",
        "selected_post_records",
        "source_post_record",
    } <= owned_identifiers


def test_post_content_backfill_preserves_operator_contracts() -> None:
    """Keep CLI, aggregate output, persistence, and close contracts stable."""
    script_source = SCRIPT_PATH.read_text(encoding="utf-8")

    for contract_literal in (
        '"--target-dsn"',
        '"--post-id"',
        '"--limit"',
        '"--all"',
        '"--normalize-only"',
        '"requested_posts"',
        '"selected_posts"',
        '"processed_posts"',
        '"described_posts"',
        '"described_images"',
        '"described_regions"',
        '"embedding_rows"',
        '"skipped_posts"',
        "from source_post",
        "post_content_unit",
        "post_content_embedding",
        "persist_post_content(",
        "record_post_content_backfill_success(",
        "await database_connection.close()",
    ):
        assert contract_literal in script_source

    for generic_sql_alias in (
        "source_post post",
        "source_post real_post",
        "post_content_unit unit",
        "post_content_embedding embedding",
        "corporate_entity entity",
    ):
        assert generic_sql_alias not in script_source

    for semantic_sql_alias in (
        "source_post source_record",
        "source_post attributed_post",
        "post_content_unit content_unit",
        "post_content_embedding content_embedding",
        "corporate_entity owning_entity",
    ):
        assert semantic_sql_alias in script_source
