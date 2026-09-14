"""Naming contract for the bounded post-Keyman operator command."""

from __future__ import annotations

import ast
from pathlib import Path


SCRIPT_PATH = Path(__file__).parents[1] / "scripts" / "backfill_post_keymen.py"


def test_post_keyman_backfill_uses_bounded_context_identifiers() -> None:
    """Keep owned command, database, record, and result names semantic."""
    syntax_tree = ast.parse(SCRIPT_PATH.read_text(encoding="utf-8"))
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

    forbidden_generic_identifiers = {
        "_run",
        "args",
        "conn",
        "exc",
        "failures",
        "limit",
        "mention_count",
        "name",
        "names",
        "normalized",
        "parser",
        "pool",
        "processed",
        "row",
        "rows",
        "selector",
        "settings",
    }
    assert owned_identifiers.isdisjoint(forbidden_generic_identifiers)
    assert {
        "_run_post_keyman_backfill",
        "command_arguments",
        "database_connection",
        "database_pool",
        "post_records",
        "processed_post_count",
        "runtime_settings",
    } <= owned_identifiers


def test_post_keyman_backfill_preserves_operator_contract() -> None:
    """Keep released CLI flags and JSON result fields at the adapter boundary."""
    script_source = SCRIPT_PATH.read_text(encoding="utf-8")
    for contract_literal in (
        '"--post-id"',
        '"--all"',
        '"--limit"',
        '"--post-timeout"',
        '"failed_posts"',
        '"failure_types"',
        '"mentions_persisted"',
        '"processed_posts"',
        '"requested_posts"',
    ):
        assert contract_literal in script_source

    syntax_tree = ast.parse(script_source)
    asynchronous_entrypoint_calls = {
        syntax_node.func.id
        for syntax_node in ast.walk(syntax_tree)
        if isinstance(syntax_node, ast.Call) and isinstance(syntax_node.func, ast.Name)
    }
    assert "_run_post_keyman_backfill" in asynchronous_entrypoint_calls
