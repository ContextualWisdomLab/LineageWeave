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


@pytest.mark.parametrize("relative_path", SQL_REVIEW_PATHS)
def test_reviewed_asyncpg_calls_use_literal_statements(relative_path: str) -> None:
    """Reviewed database calls keep SQL syntax literal at each call boundary."""
    source = (ROOT / relative_path).read_text(encoding="utf-8")
    tree = ast.parse(source, filename=relative_path)
    violations: list[int] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or not node.args:
            continue
        if not isinstance(node.func, ast.Attribute) or node.func.attr not in ASYNC_STATEMENT_METHODS:
            continue
        statement = node.args[0]
        if not (isinstance(statement, ast.Constant) and isinstance(statement.value, str)):
            violations.append(node.lineno)

    assert not violations, f"non-literal asyncpg statements at lines {violations} in {relative_path}"
    assert "nosemgrep:" not in source


def test_post_structure_protocol_stub_fails_explicitly() -> None:
    """The protocol method cannot silently return ``None`` when invoked directly."""
    with pytest.raises(NotImplementedError):
        PostStructureClient.infer(object(), "title", [])
