"""Naming and external-contract checks for issue-ticket persistence."""

from __future__ import annotations

import ast
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).parents[1]
ISSUE_TICKET_INGESTION_PATH = (
    REPOSITORY_ROOT / "backend" / "app" / "issue_ticket_ingestion.py"
)


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


def test_issue_ticket_ingestion_uses_semantic_owned_identifiers() -> None:
    """Keep persistence rows, labels, and connections tied to ticket roles."""
    syntax_tree = ast.parse(ISSUE_TICKET_INGESTION_PATH.read_text(encoding="utf-8"))
    owned_identifiers = _owned_identifiers(syntax_tree)

    assert not (
        {
            "code",
            "conn",
            "existing",
            "labeled",
            "labels",
            "row",
            "rows",
            "ticket",
            "tickets",
        }
        & owned_identifiers
    )
    assert {
        "database_connection",
        "existing_ticket_row",
        "issue_ticket",
        "issue_ticket_row",
        "issue_ticket_rows",
        "issue_tickets",
        "labeled_issue_tickets",
        "ticket_status_code",
        "ticket_status_labels",
        "updated_ticket_row",
    } <= owned_identifiers


def test_issue_ticket_external_contracts_remain_stable() -> None:
    """Preserve released JSON fields and PostgreSQL object names."""
    source_text = ISSUE_TICKET_INGESTION_PATH.read_text(encoding="utf-8")

    for contract_literal in (
        '"issue_ticket_id"',
        '"post_id"',
        '"ticket_status_code"',
        '"ticket_status_label"',
        '"ticket_title"',
        '"assigned_account_id"',
        '"due_date"',
        '"commitment_summary"',
        "from issue_ticket",
        "insert into issue_ticket",
        "update issue_ticket",
    ):
        assert contract_literal in source_text
