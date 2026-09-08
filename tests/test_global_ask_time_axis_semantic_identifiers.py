"""Naming contracts for Global Ask time-axis source selection."""

from __future__ import annotations

import ast
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).parents[1]
TIME_AXIS_SOURCE_PATH = REPOSITORY_ROOT / "lineageweave" / "ask_time_axis.py"
POST_CHAT_SOURCE_PATH = REPOSITORY_ROOT / "backend" / "app" / "post_chat_ingestion.py"
TIME_AXIS_TEST_PATH = REPOSITORY_ROOT / "tests" / "test_ask_time_axis.py"
FORBIDDEN_IDENTIFIERS = {
    "channel",
    "conn",
    "day",
    "end",
    "index",
    "instant",
    "row",
    "rows",
    "sources",
    "start",
    "target",
    "value",
}
REQUIRED_IDENTIFIERS = {
    "calendar_day",
    "candidate_channel_code",
    "candidate_post_row",
    "channel_candidate_ids",
    "database_connection",
    "filter_instant",
    "lineage_edge_row",
    "range_end",
    "range_start",
    "source_documents",
    "source_post_row",
    "source_post_rows",
    "timestamp_value",
    "visible_post_row",
}


def _owned_identifiers(syntax_tree: ast.AST) -> set[str]:
    """Collect repository-owned definitions, arguments, and assignment targets."""
    semantic_identifiers: set[str] = set()
    for syntax_node in ast.walk(syntax_tree):
        if isinstance(
            syntax_node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)
        ):
            semantic_identifiers.add(syntax_node.name)
        elif isinstance(syntax_node, ast.arg):
            semantic_identifiers.add(syntax_node.arg)
        elif isinstance(syntax_node, ast.Name) and isinstance(
            syntax_node.ctx, ast.Store
        ):
            semantic_identifiers.add(syntax_node.id)
    return semantic_identifiers


def _named_function(syntax_tree: ast.Module, function_name: str) -> ast.AST:
    """Return one required top-level function from a parsed module."""
    for syntax_node in syntax_tree.body:
        if isinstance(syntax_node, (ast.FunctionDef, ast.AsyncFunctionDef)) and (
            syntax_node.name == function_name
        ):
            return syntax_node
    raise AssertionError(f"missing function: {function_name}")


def test_global_ask_time_axis_uses_semantic_owned_identifiers() -> None:
    """Keep time selection, source retrieval, and fixtures domain-specific."""
    time_axis_tree = ast.parse(TIME_AXIS_SOURCE_PATH.read_text(encoding="utf-8"))
    post_chat_tree = ast.parse(POST_CHAT_SOURCE_PATH.read_text(encoding="utf-8"))
    time_axis_test_tree = ast.parse(TIME_AXIS_TEST_PATH.read_text(encoding="utf-8"))

    time_axis_identifiers = _owned_identifiers(time_axis_tree)
    time_axis_identifiers.update(
        _owned_identifiers(_named_function(post_chat_tree, "gather_global_chat_sources"))
    )
    time_axis_identifiers.update(_owned_identifiers(time_axis_test_tree))

    assert not (FORBIDDEN_IDENTIFIERS & time_axis_identifiers)
    assert REQUIRED_IDENTIFIERS <= time_axis_identifiers


def test_global_ask_time_axis_external_contracts_remain_stable() -> None:
    """Preserve source-post columns, evidence facts, and public helper names."""
    time_axis_source = TIME_AXIS_SOURCE_PATH.read_text(encoding="utf-8")
    post_chat_source = POST_CHAT_SOURCE_PATH.read_text(encoding="utf-8")

    for contract_literal in (
        '"event_occurred_at"',
        '"created_at"',
        "ask_filter_instant",
        "row_matches_time_range",
        "time_axis_evidence_fact",
    ):
        assert contract_literal in time_axis_source
    for contract_literal in (
        "from source_post",
        '"post_id"',
        '"visibility_code"',
        '"external_claim_facts"',
        '"source_post_revision_id"',
    ):
        assert contract_literal in post_chat_source
