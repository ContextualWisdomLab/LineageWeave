"""Decide which pytest files need optional extras that may be absent.

OpenCode coverage-evidence runs in a networkless sandbox that supplies
pytest and coverage but not LineageWeave's optional backend extras
(``asyncpg``, ``pg8000``, ``redis``, ``fast_mlsirm``, ``numpy``). Hosted CI
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
    "pg8000",
    "redis",
    "fast_mlsirm",
    "numpy",
)

_HELPER_TEST_NAME = "test_optional_extra_collection.py"
_REPOSITORY_ROOT = Path(__file__).resolve().parents[1]


def _imported_module_names(source: str) -> frozenset[str]:
    """Return exact top-level module paths from syntactically valid imports.

    For ``from package import submodule`` both the package and candidate
    submodule path are retained. The local-source resolver later decides
    whether that candidate is a real repository module, which lets collection
    tracing follow imports such as ``from lineageweave import postgres_sync``
    without mistaking ordinary imported attributes for modules.
    """
    try:
        tree = ast.parse(source)
    except (SyntaxError, ValueError):
        return frozenset()
    imported: set[str] = set()
    for node in tree.body:
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module)
            if node.level == 0:
                imported.update(
                    f"{node.module}.{alias.name}"
                    for alias in node.names
                    if alias.name != "*"
                )
    return frozenset(imported)


def _local_module_source(module_name: str) -> Path | None:
    """Resolve one absolute local module name without importing its code."""
    relative = Path(*module_name.split("."))
    module_path = _REPOSITORY_ROOT / relative.with_suffix(".py")
    if module_path.is_file():
        return module_path
    package_path = _REPOSITORY_ROOT / relative / "__init__.py"
    return package_path if package_path.is_file() else None


def _transitive_imported_module_names(collection_path: Path) -> frozenset[str]:
    """Return direct and local-transitive imports for one collection path."""
    imported: set[str] = set()
    pending = [collection_path]
    visited: set[Path] = set()
    while pending:
        source_path = pending.pop()
        if source_path in visited:
            continue
        visited.add(source_path)
        try:
            source = source_path.read_text(encoding="utf-8")
        except (OSError, UnicodeError):
            continue
        direct = _imported_module_names(source)
        imported.update(direct)
        for module_name in direct:
            local_source = _local_module_source(module_name)
            if local_source is not None and local_source not in visited:
                pending.append(local_source)
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
    imported_modules = _transitive_imported_module_names(collection_path)
    for name in missing:
        if any(
            module_name == name or module_name.startswith(f"{name}.")
            for module_name in imported_modules
        ):
            return True
    return False
