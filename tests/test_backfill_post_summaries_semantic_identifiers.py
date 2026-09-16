"""Contract tests for semantic post-summary backfill identifiers."""

from __future__ import annotations

import ast
from pathlib import Path

SOURCE_PATH = Path(__file__).parents[1] / "scripts" / "backfill_post_summaries.py"

FORBIDDEN_IDENTIFIERS = {
    "_gateway_config",
    "_load_posts",
    "_parser",
    "_semantic_hints",
    "api_key",
    "args",
    "base_url",
    "conn",
    "exc",
    "failures",
    "limit",
    "name",
    "normalized",
    "post_ids",
    "result",
    "row",
    "rows",
    "summary",
}
REQUIRED_IDENTIFIERS = {
    "_load_summary_source_posts",
    "_orchestrator_gateway_config",
    "_post_semantic_hints",
    "_post_summary_backfill_parser",
    "argument_parser",
    "backfill_summary",
    "command_arguments",
    "database_connection",
    "failure_type_counts",
    "failure_type_name",
    "normalized_post_content",
    "orchestrator_api_key",
    "orchestrator_base_url",
    "post_embedding_client",
    "post_failure",
    "post_limit",
    "post_structure_client",
    "post_summary",
    "post_summary_client",
    "post_vision_client",
    "requested_post_ids",
    "source_post_record",
    "source_post_records",
}


def _owned_identifiers(source_tree: ast.AST) -> set[str]:
    """Collect package-owned definitions, arguments, and assignment targets."""
    identifiers: set[str] = set()
    for syntax_node in ast.walk(source_tree):
        if isinstance(
            syntax_node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)
        ):
            identifiers.add(syntax_node.name)
        elif isinstance(syntax_node, ast.arg):
            identifiers.add(syntax_node.arg)
        elif isinstance(syntax_node, ast.ExceptHandler) and syntax_node.name:
            identifiers.add(syntax_node.name)
        elif isinstance(syntax_node, ast.Name) and isinstance(
            syntax_node.ctx, ast.Store
        ):
            identifiers.add(syntax_node.id)
    return identifiers


def test_post_summary_backfill_uses_semantic_private_identifiers() -> None:
    """Require semantic names across the complete private operator surface."""
    source_tree = ast.parse(SOURCE_PATH.read_text(encoding="utf-8"))
    identifiers = _owned_identifiers(source_tree)
    assert not (FORBIDDEN_IDENTIFIERS & identifiers)
    assert REQUIRED_IDENTIFIERS <= identifiers


def test_post_summary_backfill_preserves_external_contract() -> None:
    """Keep existing CLI, JSON, database, and orchestrator boundary contracts."""
    source = SOURCE_PATH.read_text(encoding="utf-8")
    required_literals = {
        "--target-dsn",
        "--post-id",
        "--limit",
        "--all",
        '"requested_posts"',
        '"selected_posts"',
        '"processed_posts"',
        '"project_mentions"',
        '"failed_posts"',
        '"failure_types"',
        "await database_connection.close()",
        "asyncpg.connect(target_dsn)",
    }
    assert all(contract_literal in source for contract_literal in required_literals)


def test_post_summary_backfill_functions_have_docstrings() -> None:
    """Require complete function documentation for the touched operator."""
    source_tree = ast.parse(SOURCE_PATH.read_text(encoding="utf-8"))
    function_nodes = [
        syntax_node
        for syntax_node in ast.walk(source_tree)
        if isinstance(syntax_node, (ast.FunctionDef, ast.AsyncFunctionDef))
    ]
    assert function_nodes
    assert all(ast.get_docstring(function_node) for function_node in function_nodes)
