"""Repository-wide public docstring contract."""

import ast
from pathlib import Path


_ROOT = Path(__file__).resolve().parents[1]


def _missing_public_docstrings(packages: tuple[Path, ...], *, root: Path) -> list[str]:
    """Return source locations for public definitions without docstrings."""

    missing: list[str] = []
    for package in packages:
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
                    missing.append(f"{path.relative_to(root)}:{node.lineno}:{node.name}")
    return missing


def test_production_public_definitions_have_docstrings() -> None:
    """Keep public production definitions documented as the codebase evolves."""

    missing = _missing_public_docstrings(
        (_ROOT / "lineageweave", _ROOT / "backend" / "app"),
        root=_ROOT,
    )

    assert missing == []


def test_docstring_contract_reports_a_missing_public_definition(tmp_path: Path) -> None:
    """Name the exact synthetic source location a beginner must repair."""

    package = tmp_path / "synthetic_package"
    package.mkdir()
    (package / "module.py").write_text(
        "def undocumented_public_function():\n    return 'synthetic'\n",
        encoding="utf-8",
    )

    assert _missing_public_docstrings((package,), root=tmp_path) == [
        "synthetic_package/module.py:1:undocumented_public_function"
    ]
