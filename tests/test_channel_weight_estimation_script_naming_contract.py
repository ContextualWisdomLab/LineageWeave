"""Naming contract for the channel-weight estimation operator script."""

from __future__ import annotations

import ast
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
ESTIMATION_SCRIPT = REPOSITORY_ROOT / "scripts" / "estimate_channel_weights.py"


def test_channel_weight_estimation_uses_bounded_operation_name() -> None:
    """Require the async operator entry point to state the estimation it runs."""
    syntax_tree = ast.parse(ESTIMATION_SCRIPT.read_text(encoding="utf-8"))
    async_functions = {
        node.name: node
        for node in ast.walk(syntax_tree)
        if isinstance(node, ast.AsyncFunctionDef)
    }

    assert "_run_channel_weight_estimation" in async_functions
    assert "_run" not in async_functions
    operation = async_functions["_run_channel_weight_estimation"]
    assert operation.args.args[0].arg == "estimation_arguments"


def test_channel_weight_estimation_main_uses_semantic_parsed_arguments() -> None:
    """Keep parsed command-line arguments explicit at the script boundary."""
    source_text = ESTIMATION_SCRIPT.read_text(encoding="utf-8")

    assert "estimation_arguments = parser.parse_args()" in source_text
    assert "asyncio.run(_run_channel_weight_estimation(estimation_arguments))" in source_text
    assert "args = parser.parse_args()" not in source_text
