"""Static review contracts for SQL composition and protocol method stubs."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from lineageweave.post_structure import PostStructureClient


ROOT = Path(__file__).resolve().parents[1]
SQL_REVIEW_PATHS = (
    "backend/app/customer_hint_ingestion.py",
    "backend/app/demo_scope.py",
    "backend/app/entity_relationship_ingestion.py",
    "lineageweave/synthetic_seed_cleanup.py",
    "scripts/backfill_post_content.py",
    "scripts/backfill_post_keymen.py",
    "scripts/backfill_post_summaries.py",
)
ASYNC_STATEMENT_METHODS = {"execute", "fetch", "fetchrow", "fetchval"}


def _module_query_constants(tree: ast.Module) -> set[str]:
    """Return module-level names reserved for immutable SQL statements."""
    names: set[str] = set()
    for statement in tree.body:
        targets: list[ast.expr] = []
        if isinstance(statement, ast.Assign):
            targets.extend(statement.targets)
        elif isinstance(statement, ast.AnnAssign):
            targets.append(statement.target)
        for target in targets:
            if isinstance(target, ast.Name) and target.id.isupper() and target.id.endswith(
                ("_QUERY", "_SQL")
            ):
                names.add(target.id)
    return names


@pytest.mark.parametrize("relative_path", SQL_REVIEW_PATHS)
def test_asyncpg_calls_use_literal_or_module_query_constant(relative_path: str) -> None:
    """Reviewed database calls must not construct their statement at the call site."""
    source = (ROOT / relative_path).read_text(encoding="utf-8")
    tree = ast.parse(source, filename=relative_path)
    query_constants = _module_query_constants(tree)
    violations: list[int] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or not node.args:
            continue
        if not isinstance(node.func, ast.Attribute) or node.func.attr not in ASYNC_STATEMENT_METHODS:
            continue
        statement = node.args[0]
        if isinstance(statement, ast.Constant) and isinstance(statement.value, str):
            continue
        if isinstance(statement, ast.Name) and statement.id in query_constants:
            continue
        violations.append(node.lineno)

    assert not violations, f"dynamic asyncpg statements at lines {violations} in {relative_path}"
    assert "nosemgrep:" not in source


def test_post_structure_protocol_stub_fails_explicitly() -> None:
    """The protocol method cannot silently return ``None`` when invoked directly."""
    with pytest.raises(NotImplementedError):
        PostStructureClient.infer(object(), "title", [])
