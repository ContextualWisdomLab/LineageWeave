"""Naming contracts for customer-hint resolution and ingestion."""

from __future__ import annotations

import ast
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).parents[1]
CUSTOMER_HINT_SOURCE_PATHS = (
    REPOSITORY_ROOT / "lineageweave" / "customer_hint_resolution.py",
    REPOSITORY_ROOT / "backend" / "app" / "customer_hint_ingestion.py",
    REPOSITORY_ROOT / "tests" / "test_customer_hint_resolution.py",
    REPOSITORY_ROOT / "tests" / "test_customer_hint_ingestion.py",
)
FORBIDDEN_IDENTIFIERS = {
    "args",
    "body",
    "call",
    "client",
    "conn",
    "content",
    "created",
    "existing",
    "excerpts",
    "linked",
    "prompt",
    "query",
    "result",
    "row",
    "rows",
    "seen",
    "status",
}
REQUIRED_IDENTIFIERS = {
    "completion_content_text",
    "corporate_entity_id",
    "corporate_entity_name",
    "customer_context_excerpts",
    "database_connection",
    "existing_entity_row",
    "linked_post_rows",
    "orchestrator_response_body",
    "resolution_prompt",
    "source_post_row",
    "source_post_rows",
    "verified_customer_resolution",
}


def _owned_identifiers(source_path: Path) -> set[str]:
    """Collect repository-owned definitions, arguments, and assignment targets."""
    syntax_tree = ast.parse(source_path.read_text(encoding="utf-8"))
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


def test_customer_hint_pipeline_uses_semantic_owned_identifiers() -> None:
    """Keep resolver, verification, persistence, and fixture names domain-specific."""
    customer_hint_identifiers: set[str] = set()
    for customer_hint_source_path in CUSTOMER_HINT_SOURCE_PATHS:
        customer_hint_identifiers.update(_owned_identifiers(customer_hint_source_path))

    assert not (FORBIDDEN_IDENTIFIERS & customer_hint_identifiers)
    assert REQUIRED_IDENTIFIERS <= customer_hint_identifiers


def test_customer_hint_external_contracts_remain_stable() -> None:
    """Preserve released orchestrator, SQL, and API payload contracts."""
    resolution_source = CUSTOMER_HINT_SOURCE_PATHS[0].read_text(encoding="utf-8")
    ingestion_source = CUSTOMER_HINT_SOURCE_PATHS[1].read_text(encoding="utf-8")

    for contract_literal in (
        '"messages"',
        '"role": "user"',
        '"mode": "auto"',
        '"reasoning_effort"',
        "/v1/chat/completions",
    ):
        assert contract_literal in resolution_source
    for contract_literal in (
        '"corporate_entity_id"',
        '"entity_name"',
        '"linked_post_count"',
        '"verification_evidence_url"',
        "from source_post",
        "insert into corporate_entity",
        "update source_post",
    ):
        assert contract_literal in ingestion_source
