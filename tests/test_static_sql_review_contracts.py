"""Static review contracts for SQL composition and protocol method stubs."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from lineageweave.post_structure import PostStructureClient


ROOT = Path(__file__).resolve().parents[1]
SQL_REVIEW_PATHS = (
    "backend/app/analysis_run_ingestion.py",
    "backend/app/analysis_run_start.py",
    "backend/app/customer_hint_ingestion.py",
    "backend/app/demo_scope.py",
    "backend/app/entity_relationship_ingestion.py",
    "backend/app/knowledge_graph.py",
    "backend/app/main.py",
    "backend/app/report_ingestion.py",
    "lineageweave/synthetic_seed_cleanup.py",
    "scripts/backfill_post_content.py",
    "scripts/backfill_post_keymen.py",
    "scripts/backfill_post_summaries.py",
    "scripts/queue_post_content_backfill.py",
)
ASYNC_STATEMENT_METHODS = {"execute", "fetch", "fetchrow", "fetchval"}
SQL_REVIEW_RULE = "python.lang.security.audit.sqli.asyncpg-sqli.asyncpg-sqli"
EXPECTED_SQL_SUPPRESSION_COUNT = 37


@pytest.mark.parametrize("relative_path", SQL_REVIEW_PATHS)
def test_reviewed_asyncpg_calls_are_literal_or_explicitly_audited(relative_path: str) -> None:
    """Reviewed calls are literal or carry a precise, adjacent audit suppression."""
    source = (ROOT / relative_path).read_text(encoding="utf-8")
    lines = source.splitlines()
    tree = ast.parse(source, filename=relative_path)
    violations: list[int] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or not node.args:
            continue
        if not isinstance(node.func, ast.Attribute) or node.func.attr not in ASYNC_STATEMENT_METHODS:
            continue
        statement = node.args[0]
        if isinstance(statement, ast.Constant) and isinstance(statement.value, str):
            continue
        call_line = lines[node.lineno - 1]
        preceding_line = lines[node.lineno - 2] if node.lineno > 1 else ""
        if SQL_REVIEW_RULE not in call_line or "Safe SQL:" not in preceding_line:
            violations.append(node.lineno)

    assert not violations, f"unaudited non-literal asyncpg statements at lines {violations} in {relative_path}"


def test_sql_suppressions_are_precise_adjacent_and_counted() -> None:
    """Every reviewed suppression names the exact rule and has a nearby reason."""
    suppression_sites: list[tuple[str, int]] = []
    for relative_path in SQL_REVIEW_PATHS:
        lines = (ROOT / relative_path).read_text(encoding="utf-8").splitlines()
        for line_number, line in enumerate(lines, start=1):
            if "nosemgrep:" not in line:
                continue
            preceding_line = lines[line_number - 2] if line_number > 1 else ""
            assert SQL_REVIEW_RULE in line, f"wrong Semgrep rule at {relative_path}:{line_number}"
            assert "Safe SQL:" in preceding_line, f"missing Safe SQL reason at {relative_path}:{line_number}"
            suppression_sites.append((relative_path, line_number))

    assert len(suppression_sites) == EXPECTED_SQL_SUPPRESSION_COUNT


def test_post_structure_protocol_stub_fails_explicitly() -> None:
    """The protocol method cannot silently return ``None`` when invoked directly."""
    with pytest.raises(NotImplementedError):
        PostStructureClient.infer(object(), "title", [])


def test_summary_backfill_normalizes_writing_state_codes() -> None:
    """Backfill excludes transport-padded writing rows like the API gate."""
    source = (ROOT / "scripts/backfill_post_summaries.py").read_text(encoding="utf-8")
    assert "coalesce(upper(btrim(post.source_detail_state_code)), '') <> 'W'" in source


def test_summary_backfill_uses_all_source_commercial_context_fields() -> None:
    """Seed eligibility matches the reader's complete source-context contract."""
    source = (ROOT / "scripts/backfill_post_summaries.py").read_text(encoding="utf-8")
    for field_name in (
        "source_order_pool_code",
        "source_sales_order_code",
        "source_sales_order_item_number",
        "source_inspection_point_code",
    ):
        assert f"post.{field_name}" in source
        assert f"real_post.{field_name}" in source


def test_content_backfill_normalizes_writing_state_codes() -> None:
    """Content recovery excludes padded and lower-case writing rows."""
    source = (ROOT / "scripts/queue_post_content_backfill.py").read_text(encoding="utf-8")
    assert "coalesce(upper(btrim(post.source_detail_state_code)), '') <> 'W'" in source


def test_content_backfill_uses_all_source_commercial_context_fields() -> None:
    """Content recovery queues posts identified only by commercial context."""
    source = (ROOT / "scripts/queue_post_content_backfill.py").read_text(encoding="utf-8")
    for field_name in (
        "source_order_pool_code",
        "source_sales_order_code",
        "source_sales_order_item_number",
        "source_inspection_point_code",
    ):
        assert field_name in source


@pytest.mark.parametrize(
    "relative_path, qualified_column",
    [
        ("backend/app/post_content_worker.py", "p.source_detail_state_code"),
        ("backend/app/post_content_queue.py", "post.source_detail_state_code"),
        ("scripts/queue_post_content_backfill.py", "post.source_detail_state_code"),
    ],
)
def test_post_content_writing_state_gates_are_case_insensitive(
    relative_path: str,
    qualified_column: str,
) -> None:
    """Queue and worker gates reject transport-padded lowercase writing states."""
    source = (ROOT / relative_path).read_text(encoding="utf-8")
    assert f"coalesce(upper(btrim({qualified_column})), '') <> 'W'" in source
