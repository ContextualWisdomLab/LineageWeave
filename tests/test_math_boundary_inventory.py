"""Freeze known Python numerical ownership while ADR 0208 moves it upstream."""

from __future__ import annotations

import ast
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
NUMERICAL_OWNER_MODULES = {"fast_mlsirm", "numpy", "rankweave", "scipy", "sklearn"}
KNOWN_LOCAL_NUMERICAL_FILES = {
    "lineageweave/leftover_pairs.py",
    "lineageweave/period_report.py",
    "lineageweave/post_evaluation.py",
    "lineageweave/rankweave_client.py",
    "lineageweave/reconstruct.py",
}
KNOWN_LOCAL_DIRECT_VECTOR_ARITHMETIC = {"backend/app/post_chat_ingestion.py"}


def _numerical_import_files() -> set[str]:
    """Return production Python files importing a numerical owner package."""

    found: set[str] = set()
    for base in (ROOT / "lineageweave", ROOT / "backend" / "app"):
        for path in base.rglob("*.py"):
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            imports = {
                alias.name.split(".", 1)[0]
                for node in ast.walk(tree)
                if isinstance(node, ast.Import)
                for alias in node.names
            }
            imports.update(
                node.module.split(".", 1)[0]
                for node in ast.walk(tree)
                if isinstance(node, ast.ImportFrom) and node.module
            )
            if imports & NUMERICAL_OWNER_MODULES:
                found.add(path.relative_to(ROOT).as_posix())
    return found


def test_no_new_local_numerical_owner_imports() -> None:
    """Require an ADR 0208 inventory update before local numerical scope grows."""

    assert _numerical_import_files() == KNOWN_LOCAL_NUMERICAL_FILES


def test_no_new_direct_python_vector_arithmetic() -> None:
    """Freeze direct dot/norm arithmetic until a Rust owner contract replaces it."""

    found: set[str] = set()
    for base in (ROOT / "lineageweave", ROOT / "backend" / "app"):
        for path in base.rglob("*.py"):
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            for node in ast.walk(tree):
                if not isinstance(node, ast.Call):
                    continue
                is_sqrt = (
                    isinstance(node.func, ast.Attribute)
                    and isinstance(node.func.value, ast.Name)
                    and node.func.value.id == "math"
                    and node.func.attr == "sqrt"
                )
                is_product_sum = (
                    isinstance(node.func, ast.Name)
                    and node.func.id == "sum"
                    and any(
                        isinstance(child, ast.BinOp) and isinstance(child.op, ast.Mult)
                        for child in ast.walk(node)
                    )
                )
                if is_sqrt or is_product_sum:
                    found.add(path.relative_to(ROOT).as_posix())
    assert found == KNOWN_LOCAL_DIRECT_VECTOR_ARITHMETIC
