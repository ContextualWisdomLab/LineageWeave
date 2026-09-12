"""Naming contract for the thread-group-key backfill operator script."""

from __future__ import annotations

import ast
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
BACKFILL_SCRIPT = REPOSITORY_ROOT / "scripts" / "backfill_thread_group_keys.py"


def test_thread_group_backfill_uses_bounded_operation_name() -> None:
    """Require the pooled operator coroutine to name the backfill it executes."""
    syntax_tree = ast.parse(BACKFILL_SCRIPT.read_text(encoding="utf-8"))
    async_functions = {
        node.name: node
        for node in ast.walk(syntax_tree)
        if isinstance(node, ast.AsyncFunctionDef)
    }

    assert "_run_thread_group_key_backfill" in async_functions
    assert "_run" not in async_functions
    operation = async_functions["_run_thread_group_key_backfill"]
    assert operation.args.args[0].arg == "backfill_arguments"


def test_thread_group_backfill_main_uses_semantic_parsed_arguments() -> None:
    """Keep parsed command-line arguments explicit at the script boundary."""
    source_text = BACKFILL_SCRIPT.read_text(encoding="utf-8")

    assert "backfill_arguments = parser.parse_args()" in source_text
    assert "asyncio.run(_run_thread_group_key_backfill(backfill_arguments))" in source_text
    assert "args = parser.parse_args()" not in source_text
