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
TRUSTED_SQL_NAMES = {
    "backend/app/customer_hint_ingestion.py": {
        "_RAW_BODY_SQL_CAP",
        "_SAMPLE_POST_LIMIT",
        "SOURCE_POST_ELIGIBILITY_SQL",
    },
    "backend/app/demo_scope.py": set(),
    "backend/app/entity_relationship_ingestion.py": {
        "_RELATIONSHIP_NETWORK_LIMIT",
        "SOURCE_POST_ELIGIBILITY_SQL",
    },
    "lineageweave/synthetic_seed_cleanup.py": {"table", "column"},
    "scripts/backfill_post_content.py": {"conditions", "limit_sql"},
    "scripts/backfill_post_keymen.py": {"eligibility"},
    "scripts/backfill_post_summaries.py": {"conditions", "limit_sql"},
}
TRUSTED_SQL_FUNCTIONS = {
    "source_context_present_sql",
    "_missing_source_context",
    "_has_source_context",
}


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


def _trusted_sql_fragment(node: ast.AST, relative_path: str) -> bool:
    """Allow only reviewed, fixed-schema composition inside a SQL string.

    Request values remain asyncpg parameters. The few interpolated fragments
    here are bounded constants, fixed condition lists, or identifiers escaped
    by ``_quote_identifier``; treating every f-string as a finding would make
    the contract reject the safe catalog-cleanup path as well.
    """
    allowed_names = TRUSTED_SQL_NAMES[relative_path]
    if isinstance(node, ast.Constant):
        return isinstance(node.value, str)
    if isinstance(node, ast.Name):
        return node.id in allowed_names
    if isinstance(node, ast.Call):
        if isinstance(node.func, ast.Name):
            return node.func.id in TRUSTED_SQL_FUNCTIONS and all(
                isinstance(argument, ast.Constant) for argument in node.args
            )
        if isinstance(node.func, ast.Attribute) and node.func.attr == "format":
            return _trusted_sql_fragment(node.func.value, relative_path) and all(
                _trusted_sql_fragment(keyword.value, relative_path)
                or isinstance(keyword.value, ast.Constant)
                for keyword in node.keywords
            )
        if (
            isinstance(node.func, ast.Attribute)
            and node.func.attr == "join"
            and isinstance(node.func.value, ast.Constant)
            and node.func.value.value == " and "
            and len(node.args) == 1
        ):
            return _trusted_sql_fragment(node.args[0], relative_path)
    return False


def _trusted_statement(node: ast.AST, relative_path: str) -> bool:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return True
    if isinstance(node, ast.JoinedStr):
        return all(
            _trusted_sql_fragment(value.value, relative_path)
            for value in node.values
            if isinstance(value, ast.FormattedValue)
        )
    return _trusted_sql_fragment(node, relative_path)


@pytest.mark.parametrize("relative_path", SQL_REVIEW_PATHS)
def test_asyncpg_calls_use_literal_or_module_query_constant(relative_path: str) -> None:
    """Reviewed database calls must not interpolate untrusted SQL fragments."""
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
        if isinstance(statement, ast.Name) and statement.id in query_constants:
            continue
        if _trusted_statement(statement, relative_path):
            continue
        violations.append(node.lineno)

    assert not violations, f"dynamic asyncpg statements at lines {violations} in {relative_path}"
    assert "nosemgrep:" not in source


def test_post_structure_protocol_stub_fails_explicitly() -> None:
    """The protocol method cannot silently return ``None`` when invoked directly."""
    with pytest.raises(NotImplementedError):
        PostStructureClient.infer(object(), "title", [])
