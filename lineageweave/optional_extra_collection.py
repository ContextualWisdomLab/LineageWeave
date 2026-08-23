"""Decide which pytest files need optional extras that may be absent.

OpenCode coverage-evidence runs in a networkless sandbox that supplies
pytest and coverage but not LineageWeave's optional backend extras
(``asyncpg``, ``psycopg2``, ``redis``, ``fast_mlsirm``). Hosted CI
installs those extras and collects every suite. This helper keeps
collection from failing with ``ModuleNotFoundError`` when extras are
absent, without skipping anything when they are present.
"""

from __future__ import annotations

import importlib.util
from collections.abc import Iterable
from pathlib import Path

OPTIONAL_EXTRA_MODULES: tuple[str, ...] = (
    "asyncpg",
    "psycopg2",
    "redis",
    "fast_mlsirm",
)

_BACKEND_EXTRAS: frozenset[str] = frozenset({"asyncpg", "psycopg2", "redis"})
_HELPER_TEST_NAME = "test_optional_extra_collection.py"


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
    if any(name in _BACKEND_EXTRAS for name in missing):
        if posix == "backend" or posix.startswith("backend/") or "/backend/" in posix:
            return True
    try:
        text = collection_path.read_text(encoding="utf-8")
    except OSError:
        return False
    for name in missing:
        if (
            f"import {name}" in text
            or f"from {name} " in text
            or f"from {name}." in text
        ):
            return True
        if name in _BACKEND_EXTRAS and (
            "from backend" in text or "import backend" in text
        ):
            return True
    return False
