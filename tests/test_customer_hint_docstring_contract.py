"""Docstring contract for the Customer Master ownership-separation repair."""

from __future__ import annotations

import ast
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
_EXPECTED_FUNCTIONS = {
    "backend/app/customer_hint_ingestion.py": {
        "_resolved_customer_code",
        "resolve_customer_hint",
    },
    "backend/app/post_eligibility.py": {
        "source_context_present_sql",
        "source_context_missing_sql",
        "source_post_scope_sql",
        "source_post_visible",
        "fetch_visible_customer_hint_evidence",
        "lock_visible_customer_hint_sources",
    },
    "backend/app/main.py": {
        "read_customer_master",
        "resolve_customer_master_hint",
    },
}


def _functions_by_name(relative_path: str) -> dict[str, ast.FunctionDef | ast.AsyncFunctionDef]:
    """Parse one production module and index top-level functions by exact name."""
    source = (_ROOT / relative_path).read_text(encoding="utf-8")
    tree = ast.parse(source, filename=relative_path)
    return {
        node.name: node
        for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }


def test_customer_hint_production_functions_have_docstrings() -> None:
    """Every production function owned by this repair must retain a real docstring."""
    missing_functions: list[str] = []
    missing_docstrings: list[str] = []

    for relative_path, expected_names in _EXPECTED_FUNCTIONS.items():
        functions = _functions_by_name(relative_path)
        for function_name in sorted(expected_names):
            function = functions.get(function_name)
            qualified_name = f"{relative_path}:{function_name}"
            if function is None:
                missing_functions.append(qualified_name)
                continue
            if not ast.get_docstring(function, clean=True):
                missing_docstrings.append(qualified_name)

    assert not missing_functions, f"production functions disappeared: {missing_functions}"
    assert not missing_docstrings, f"production docstrings missing: {missing_docstrings}"
