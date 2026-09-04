"""Naming contract for the bounded post-Keyman operator backfill."""

from __future__ import annotations

import ast
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
BACKFILL_SCRIPT = REPOSITORY_ROOT / "scripts" / "backfill_post_keymen.py"


def test_post_keymen_backfill_uses_bounded_operation_name() -> None:
    """Require the operator coroutine to name the operation it owns."""
    syntax_tree = ast.parse(BACKFILL_SCRIPT.read_text(encoding="utf-8"))
    async_functions = {
        node.name: node
        for node in ast.walk(syntax_tree)
        if isinstance(node, ast.AsyncFunctionDef)
    }

    assert "_run_post_keymen_backfill" in async_functions
    assert "_run" not in async_functions
    operation = async_functions["_run_post_keymen_backfill"]
    assert operation.args.args[0].arg == "backfill_arguments"


def test_post_keymen_backfill_main_uses_semantic_parsed_arguments() -> None:
    """Keep parsed command-line arguments explicit at the script boundary."""
    source_text = BACKFILL_SCRIPT.read_text(encoding="utf-8")

    assert "backfill_arguments = parser.parse_args()" in source_text
    assert "asyncio.run(_run_post_keymen_backfill(backfill_arguments))" in source_text
    assert "args = parser.parse_args()" not in source_text
