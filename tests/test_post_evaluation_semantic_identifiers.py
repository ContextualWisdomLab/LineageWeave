"""Naming contracts for post evaluation, IRT projection, and persistence."""

from __future__ import annotations

import ast
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).parents[1]
EVALUATION_SOURCE_PATHS = (
    REPOSITORY_ROOT / "lineageweave" / "post_evaluation.py",
    REPOSITORY_ROOT / "backend" / "app" / "post_evaluation_ingestion.py",
)
API_SOURCE_PATH = REPOSITORY_ROOT / "backend" / "app" / "main.py"

FORBIDDEN_IDENTIFIERS = {
    "body",
    "categories",
    "client",
    "conn",
    "result",
    "response",
    "responses",
    "row",
    "rows",
}
REQUIRED_IDENTIFIERS = {
    "criterion_response",
    "criterion_responses",
    "database_connection",
    "evaluation_row",
    "irt_response_categories",
    "judge_result",
    "orchestrator_response_body",
    "persisted_evaluation_rows",
    "post_evaluation_client",
}
API_FUNCTION_NAMES = {"evaluate_post", "read_post_evaluation"}


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


def test_post_evaluation_pipeline_uses_semantic_owned_identifiers() -> None:
    """Keep judge, IRT, database, and persisted-row names domain-specific."""
    pipeline_identifiers: set[str] = set()
    for evaluation_source_path in EVALUATION_SOURCE_PATHS:
        evaluation_source_tree = ast.parse(
            evaluation_source_path.read_text(encoding="utf-8")
        )
        pipeline_identifiers.update(_owned_identifiers(evaluation_source_tree))

    api_source_tree = ast.parse(API_SOURCE_PATH.read_text(encoding="utf-8"))
    for api_function_node in api_source_tree.body:
        if isinstance(api_function_node, ast.AsyncFunctionDef) and (
            api_function_node.name in API_FUNCTION_NAMES
        ):
            pipeline_identifiers.update(_owned_identifiers(api_function_node))

    assert not (FORBIDDEN_IDENTIFIERS & pipeline_identifiers)
    assert REQUIRED_IDENTIFIERS <= pipeline_identifiers


def test_post_evaluation_sql_uses_semantic_relation_aliases() -> None:
    """Keep repository-owned SQL aliases aligned with evaluation language."""
    ingestion_source = EVALUATION_SOURCE_PATHS[1].read_text(encoding="utf-8")

    assert "from post_evaluation_response evaluation_response" in ingestion_source
    assert "left join common_lookup_value criterion_lookup" in ingestion_source
    assert "post_evaluation_response e" not in ingestion_source
    assert "common_lookup_value v" not in ingestion_source


def test_post_evaluation_external_contracts_remain_stable() -> None:
    """Preserve API keys, persistence tables, and fast-mlsirm projection calls."""
    evaluation_source = EVALUATION_SOURCE_PATHS[0].read_text(encoding="utf-8")
    ingestion_source = EVALUATION_SOURCE_PATHS[1].read_text(encoding="utf-8")
    api_source = API_SOURCE_PATH.read_text(encoding="utf-8")

    for contract_literal in (
        '"/api/posts/{post_id}/evaluation"',
        '"/api/posts/{post_id}/evaluate"',
        '"criterion_code"',
        '"criterion_label"',
        '"response_category"',
        '"rubric_version"',
    ):
        assert contract_literal in api_source
    assert "post_evaluation_response" in ingestion_source
    assert "common_lookup_value" in ingestion_source
    assert ".to_irt_row(" in evaluation_source
