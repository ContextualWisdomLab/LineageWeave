"""Naming contract for the bounded thread-group-key backfill command."""

from __future__ import annotations

import ast
from pathlib import Path

SCRIPT_PATH = Path(__file__).parents[1] / "scripts" / "backfill_thread_group_keys.py"
BEHAVIOR_TEST_PATH = (
    Path(__file__).parents[1] / "tests" / "test_backfill_thread_group_keys.py"
)


def test_thread_group_key_backfill_uses_semantic_identifiers() -> None:
    """Keep owned command, database, record, and count names semantic."""
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
            "_run",
            "args",
            "cleared",
            "conn",
            "counts",
            "parser",
            "pool",
            "project_evidence",
            "row",
            "rows",
            "settings",
        }
    )
    assert {
        "_run_thread_group_key_backfill",
        "analysis_run_ids",
        "command_arguments",
        "database_connection",
        "database_pool",
        "runtime_settings",
        "updated_post_records",
    } <= owned_identifiers


def test_thread_group_key_backfill_preserves_operator_contract() -> None:
    """Keep the CLI flag and aggregate JSON keys at the adapter boundary."""
    script_source = SCRIPT_PATH.read_text(encoding="utf-8")
    for contract_literal in (
        '"--dry-run"',
        '"cleared_placeholder_posts"',
        '"project_secondary_evidence_posts"',
        '"dry_run"',
    ):
        assert contract_literal in script_source

    syntax_tree = ast.parse(script_source)
    called_functions = {
        syntax_node.func.id
        for syntax_node in ast.walk(syntax_tree)
        if isinstance(syntax_node, ast.Call) and isinstance(syntax_node.func, ast.Name)
    }
    assert "_run_thread_group_key_backfill" in called_functions


def test_thread_group_key_behavior_tests_use_domain_specific_test_doubles() -> None:
    """Keep repository-owned test identifiers aligned with the backfill domain."""
    test_source = BEHAVIOR_TEST_PATH.read_text(encoding="utf-8")
    syntax_tree = ast.parse(test_source)
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
        if isinstance(
            syntax_node,
            (ast.AsyncFunctionDef, ast.ClassDef, ast.FunctionDef),
        )
    )

    assert owned_identifiers.isdisjoint(
        {
            "_Connection",
            "anchored_runs",
            "backfill",
            "conn",
            "exc",
            "result",
            "rows",
            "script",
            "update",
        }
    )
    assert {
        "_ThreadGroupDatabaseConnection",
        "analysis_run_ids",
        "backfill_summary",
        "database_connection",
        "placeholder_post_rows",
        "thread_group_backfill",
        "update_query",
    } <= owned_identifiers
