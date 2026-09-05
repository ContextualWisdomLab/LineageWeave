"""Dependency-boundary contract for the translation API integration slice."""

from __future__ import annotations

import ast
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
_API_TEST = ROOT / "tests" / "test_translation_api_http.py"


def _translation_http_tests() -> list[ast.FunctionDef | ast.AsyncFunctionDef]:
    """Return focused HTTP tests that exercise the translation route."""
    tree = ast.parse(_API_TEST.read_text(encoding="utf-8"))
    return [
        node
        for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and node.name.startswith("test_translation_screen")
    ]


def test_translation_api_has_focused_http_contract() -> None:
    """The authenticated API slice must not be covered by an empty test selection."""
    assert _API_TEST.exists(), "translation API requires a focused HTTP contract test module"
    assert _translation_http_tests(), "translation API requires at least one test_translation_screen* HTTP test"


def test_translation_api_tests_do_not_add_psycopg2_callers() -> None:
    """The #929 API slice must not reintroduce a caller owned by #910/#911 retirement."""
    for test in _translation_http_tests():
        dotted_names = {
            ast.unparse(node)
            for node in ast.walk(test)
            if isinstance(node, (ast.Name, ast.Attribute))
        }
        assert not any(name == "psycopg2" or name.startswith("psycopg2.") for name in dotted_names), (
            f"{test.name} reintroduces direct psycopg2 reachability"
        )
