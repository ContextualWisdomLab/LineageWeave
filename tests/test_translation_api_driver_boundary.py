"""Dependency-boundary contract for the translation API integration slice."""

from __future__ import annotations

import ast
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
_API_TEST = ROOT / "backend" / "tests" / "test_api.py"


def test_translation_api_tests_do_not_add_psycopg2_callers() -> None:
    """The #929 API slice must not reintroduce a caller owned by #910/#911 retirement."""
    tree = ast.parse(_API_TEST.read_text(encoding="utf-8"))
    translation_tests = [
        node
        for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and node.name.startswith("test_translation_screen")
    ]
    for test in translation_tests:
        dotted_names = {
            ast.unparse(node)
            for node in ast.walk(test)
            if isinstance(node, (ast.Name, ast.Attribute))
        }
        assert not any(name == "psycopg2" or name.startswith("psycopg2.") for name in dotted_names), (
            f"{test.name} reintroduces direct psycopg2 reachability"
        )
