"""Safety contract for the bounded post-Keyman operator timeout."""

from __future__ import annotations

import ast
import math
from pathlib import Path

import pytest


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
BACKFILL_SCRIPT = REPOSITORY_ROOT / "scripts" / "backfill_post_keymen.py"


def _load_timeout_validator():
    """Load only the pure timeout validator without importing operator dependencies."""
    syntax_tree = ast.parse(BACKFILL_SCRIPT.read_text(encoding="utf-8"))
    validator = next(
        (
            node
            for node in syntax_tree.body
            if isinstance(node, ast.FunctionDef)
            and node.name == "_post_timeout_is_valid"
        ),
        None,
    )
    assert validator is not None, "operator must expose a pure timeout admission check"
    namespace = {"math": math}
    module = ast.fix_missing_locations(ast.Module(body=[validator], type_ignores=[]))
    exec(compile(module, str(BACKFILL_SCRIPT), "exec"), namespace)
    return namespace["_post_timeout_is_valid"]


@pytest.mark.parametrize("invalid_timeout", [0.0, -1.0, math.nan, math.inf, -math.inf])
def test_post_keymen_backfill_rejects_non_positive_or_non_finite_timeout(
    invalid_timeout: float,
) -> None:
    validator = _load_timeout_validator()

    assert validator(invalid_timeout) is False


@pytest.mark.parametrize("invalid_timeout", [True, False, "240", None])
def test_post_keymen_backfill_rejects_non_numeric_or_boolean_timeout(
    invalid_timeout: object,
) -> None:
    """Reject malformed programmatic values instead of relying on argparse coercion."""
    validator = _load_timeout_validator()

    assert validator(invalid_timeout) is False


def test_post_keymen_backfill_accepts_positive_finite_timeout() -> None:
    validator = _load_timeout_validator()

    assert validator(0.001) is True
    assert validator(240.0) is True


def test_main_routes_timeout_through_the_admission_check() -> None:
    syntax_tree = ast.parse(BACKFILL_SCRIPT.read_text(encoding="utf-8"))
    main_function = next(
        node
        for node in syntax_tree.body
        if isinstance(node, ast.FunctionDef) and node.name == "main"
    )

    assert any(
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "_post_timeout_is_valid"
        for node in ast.walk(main_function)
    )


def test_programmatic_runner_revalidates_timeout_before_external_work() -> None:
    """Keep direct callers behind the same bounded timeout admission contract."""
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
        and node.func.id == "_post_timeout_is_valid"
    ]
    assert calls, "programmatic runner must revalidate timeout before provider/database work"
