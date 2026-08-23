"""Decide which pytest files need optional extras that may be absent.

OpenCode coverage-evidence runs in a networkless sandbox that supplies
pytest and coverage but not LineageWeave's optional backend extras
(``asyncpg``, ``psycopg2``, ``redis``, ``fast_mlsirm``, ``numpy``). Hosted CI
installs those extras and collects every suite. This helper keeps
collection from failing with ``ModuleNotFoundError`` when extras are
absent, without skipping anything when they are present.
"""

from __future__ import annotations

import ast
import importlib.util
from collections.abc import Iterable
from pathlib import Path

OPTIONAL_EXTRA_MODULES: tuple[str, ...] = (
    "asyncpg",
    "psycopg2",
    "redis",
    "fast_mlsirm",
    "numpy",
)

_BACKEND_EXTRAS: frozenset[str] = frozenset(OPTIONAL_EXTRA_MODULES)
_OPTIONAL_EXTRA_IMPORTERS: dict[str, tuple[str, ...]] = {
    "asyncpg": (
        "scripts.import_postgresql_posts",
        "scripts.seed_demo_data",
    ),
    "fast_mlsirm": (
        "lineageweave.period_report",
        "lineageweave.post_evaluation",
    ),
    "numpy": ("lineageweave.period_report",),
}
_HELPER_TEST_NAME = "test_optional_extra_collection.py"


def _imported_module_names(source: str) -> frozenset[str]:
    """Return exact top-level module paths from syntactically valid imports."""
    try:
        tree = ast.parse(source)
    except (SyntaxError, ValueError):
        return frozenset()
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module)
    return frozenset(imported)


def missing_optional_extra_modules(
    module_names: Iterable[str] = OPTIONAL_EXTRA_MODULES,
) -> tuple[str, ...]:
    """Return optional extra names the current interpreter cannot import."""
    return tuple(
        name for name in module_names if importlib.util.find_spec(name) is None
    )


def collection_path_requires_missing_extras(
    collection_path: Path,
    missing_modules: Iterable[str],
) -> bool:
    """Return whether collecting this path would import a missing extra."""
    missing = tuple(missing_modules)
    if not missing:
        return False
    if collection_path.suffix != ".py":
        return False
    if collection_path.name == _HELPER_TEST_NAME:
        return False
    posix = collection_path.as_posix()
    if any(name in _BACKEND_EXTRAS for name in missing) and (
        posix == "backend" or posix.startswith("backend/") or "/backend/" in posix
    ):
        return True
    try:
        text = collection_path.read_text(encoding="utf-8")
    except OSError:
        return False
    imported_modules = _imported_module_names(text)
    for name in missing:
        for imported_name in (name, *_OPTIONAL_EXTRA_IMPORTERS.get(name, ())):
            if any(
                module_name == imported_name
                or module_name.startswith(f"{imported_name}.")
                for module_name in imported_modules
            ):
                return True
        if name in _BACKEND_EXTRAS and any(
            module_name == "backend" or module_name.startswith("backend.")
            for module_name in imported_modules
        ):
            return True
    return False
