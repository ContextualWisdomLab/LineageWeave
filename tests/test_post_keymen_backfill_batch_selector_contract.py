"""Safety contract for the post-Keyman operator batch selector."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
BACKFILL_SCRIPT = REPOSITORY_ROOT / "scripts" / "backfill_post_keymen.py"


def _load_batch_selector_validator():
    """Load only the pure batch-selector validator without operator dependencies."""
    syntax_tree = ast.parse(BACKFILL_SCRIPT.read_text(encoding="utf-8"))
    validator = next(
        (
            node
            for node in syntax_tree.body
            if isinstance(node, ast.FunctionDef)
            and node.name == "_post_all_is_valid"
        ),
        None,
    )
    assert validator is not None, "operator must expose a pure batch-selector admission check"
    namespace: dict[str, object] = {}
    module = ast.fix_missing_locations(ast.Module(body=[validator], type_ignores=[]))
    exec(compile(module, str(BACKFILL_SCRIPT), "exec"), namespace)
    return namespace["_post_all_is_valid"]


def test_post_keymen_backfill_accepts_boolean_batch_selector() -> None:
    validator = _load_batch_selector_validator()

    assert validator(False) is True
    assert validator(True) is True


@pytest.mark.parametrize("invalid_selector", [0, 1, "false", "true", None, [], {}])
def test_post_keymen_backfill_rejects_non_boolean_batch_selector(
    invalid_selector: object,
) -> None:
    """Reject transport-shaped values whose truthiness could select batch mode."""
    validator = _load_batch_selector_validator()

    assert validator(invalid_selector) is False


def test_programmatic_runner_revalidates_batch_selector_before_external_work() -> None:
    """Keep direct callers behind the same selector-mode admission boundary."""
    syntax_tree = ast.parse(BACKFILL_SCRIPT.read_text(encoding="utf-8"))
    runner = next(
        node
        for node in syntax_tree.body
        if isinstance(node, ast.AsyncFunctionDef)
        and node.name == "_run_post_keymen_backfill"
    )

    calls = [
        node
        for node in ast.walk(runner)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "_post_all_is_valid"
    ]
    assert calls, "programmatic runner must revalidate batch selector before external work"
