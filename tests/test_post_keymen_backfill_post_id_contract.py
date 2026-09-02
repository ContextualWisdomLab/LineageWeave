"""Identity admission contract for the bounded post-Keyman operator selector."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
BACKFILL_SCRIPT = REPOSITORY_ROOT / "scripts" / "backfill_post_keymen.py"


def _load_post_id_validator():
    """Load only the pure post-id validator without importing operator dependencies."""
    syntax_tree = ast.parse(BACKFILL_SCRIPT.read_text(encoding="utf-8"))
    validator = next(
        (
            node
            for node in syntax_tree.body
            if isinstance(node, ast.FunctionDef)
            and node.name == "_post_id_is_valid"
        ),
        None,
    )
    assert validator is not None, "operator must expose a pure post-id admission check"
    namespace: dict[str, object] = {}
    module = ast.fix_missing_locations(ast.Module(body=[validator], type_ignores=[]))
    exec(compile(module, str(BACKFILL_SCRIPT), "exec"), namespace)
    return namespace["_post_id_is_valid"]


@pytest.mark.parametrize(
    "invalid_post_id",
    ["", " ", "\t", "post-123 ", " post-123", "post-123\n"],
)
def test_post_keymen_backfill_rejects_blank_or_padded_explicit_post_id(
    invalid_post_id: str,
) -> None:
    validator = _load_post_id_validator()

    assert validator(invalid_post_id) is False


@pytest.mark.parametrize("invalid_post_id", [7, True, ["post-123"], {"id": "post-123"}])
def test_post_keymen_backfill_rejects_non_string_explicit_post_id(
    invalid_post_id: object,
) -> None:
    """Do not let truthy transport values reach string operations or identity lookup."""
    validator = _load_post_id_validator()

    assert validator(invalid_post_id) is False


def test_post_keymen_backfill_accepts_absent_or_exact_post_id() -> None:
    validator = _load_post_id_validator()

    assert validator(None) is True
    assert validator("post-123") is True


def test_main_routes_post_id_through_the_admission_check() -> None:
    syntax_tree = ast.parse(BACKFILL_SCRIPT.read_text(encoding="utf-8"))
    main_function = next(
        node
        for node in syntax_tree.body
        if isinstance(node, ast.FunctionDef) and node.name == "main"
    )

    assert any(
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "_post_id_is_valid"
        for node in ast.walk(main_function)
    )
