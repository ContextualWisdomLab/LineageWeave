"""Repository-wide public docstring contract."""

import ast
from pathlib import Path


_ROOT = Path(__file__).resolve().parents[1]


def test_production_public_definitions_have_docstrings() -> None:
    """Keep public production definitions documented as the codebase evolves."""
    missing: list[str] = []
    for package in (_ROOT / "lineageweave", _ROOT / "backend" / "app"):
        for path in package.rglob("*.py"):
            if path.name == "__init__.py":
                continue
            tree = ast.parse(path.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if (
                    isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
                    and not node.name.startswith("_")
                    and ast.get_docstring(node) is None
                ):
                    missing.append(f"{path.relative_to(_ROOT)}:{node.lineno}:{node.name}")

    assert missing == []
