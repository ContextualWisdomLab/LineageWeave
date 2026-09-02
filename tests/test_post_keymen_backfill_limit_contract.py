"""Safety contract for the bounded post-Keyman operator batch limit."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
BACKFILL_SCRIPT = REPOSITORY_ROOT / "scripts" / "backfill_post_keymen.py"


def _load_limit_validator():
    """Load only the pure limit validator without importing operator dependencies."""
    syntax_tree = ast.parse(BACKFILL_SCRIPT.read_text(encoding="utf-8"))
    validator = next(
        (
            node
            for node in syntax_tree.body
            if isinstance(node, ast.FunctionDef)
            and node.name == "_post_limit_is_valid"
        ),
        None,
    )
    assert validator is not None, "operator must expose a pure batch-limit admission check"
    namespace: dict[str, object] = {}
    module = ast.fix_missing_locations(ast.Module(body=[validator], type_ignores=[]))
    exec(compile(module, str(BACKFILL_SCRIPT), "exec"), namespace)
    return namespace["_post_limit_is_valid"]


@pytest.mark.parametrize("invalid_limit", [0, -1, True, False, 1.0, "1", None])
def test_post_keymen_backfill_rejects_malformed_batch_limit(invalid_limit: object) -> None:
    """Reject malformed direct-call limits instead of relying on argparse coercion."""
    validator = _load_limit_validator()

    assert validator(invalid_limit) is False


def test_post_keymen_backfill_accepts_positive_integer_batch_limit() -> None:
    validator = _load_limit_validator()

    assert validator(1) is True
    assert validator(100) is True


def test_main_routes_limit_through_the_admission_check() -> None:
    syntax_tree = ast.parse(BACKFILL_SCRIPT.read_text(encoding="utf-8"))
    main_function = next(
        node
        for node in syntax_tree.body
        if isinstance(node, ast.FunctionDef) and node.name == "main"
    )

    assert any(
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "_post_limit_is_valid"
        for node in ast.walk(main_function)
    )


def test_programmatic_runner_revalidates_limit_before_external_work() -> None:
    """Keep direct callers behind the same bounded batch admission contract."""
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
        and node.func.id == "_post_limit_is_valid"
    ]
    assert calls, "programmatic runner must revalidate limit before provider/database work"
