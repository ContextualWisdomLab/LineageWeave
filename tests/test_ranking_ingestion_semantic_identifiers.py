"""Naming and authorization contracts for RankWeave ingestion."""

from __future__ import annotations

import ast
import asyncio
from pathlib import Path
from typing import Any

from backend.app.ranking_ingestion import load_visible_ranking_posts

REPOSITORY_ROOT = Path(__file__).parents[1]
RANKING_INGESTION_PATH = REPOSITORY_ROOT / "backend" / "app" / "ranking_ingestion.py"
MAIN_PATH = REPOSITORY_ROOT / "backend" / "app" / "main.py"


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


def test_ranking_ingestion_uses_semantic_owned_identifiers() -> None:
    """Keep authorization and ranking projection names domain-specific."""
    ranking_tree = ast.parse(RANKING_INGESTION_PATH.read_text(encoding="utf-8"))
    main_tree = ast.parse(MAIN_PATH.read_text(encoding="utf-8"))
    ranking_identifiers = _owned_identifiers(ranking_tree)
    ranking_identifiers.update(_owned_identifiers(_named_function(main_tree, "read_rankings")))

    assert not (
        {"_row", "account", "conn", "pool", "posts", "row"}
        & ranking_identifiers
    )
    assert {
        "current_account",
        "database_connection",
        "database_pool",
        "source_post_row",
        "visible_post_row",
        "visible_ranking_posts",
    } <= ranking_identifiers


class RecordingDatabaseConnection:
    """Return deterministic source-post rows and retain the issued SQL."""

    def __init__(self) -> None:
        """Prepare one visible and one hidden synthetic post."""
        self.executed_query = ""

    async def fetch(self, query_text: str) -> list[dict[str, Any]]:
        """Record the parameter-free authorized source-post query."""
        self.executed_query = query_text
        return [
            {"post_id": "visible-post", "visibility_code": "public"},
            {"post_id": "hidden-post", "visibility_code": "private"},
        ]


def test_ranking_ingestion_preserves_abac_filter_and_source_contract() -> None:
    """Return only source posts admitted by the caller's ABAC decision."""
    database_connection = RecordingDatabaseConnection()
    visible_ranking_posts = asyncio.run(
        load_visible_ranking_posts(
            database_connection,
            lambda source_post_row: source_post_row["visibility_code"] == "public",
        )
    )

    assert visible_ranking_posts == [
        {"post_id": "visible-post", "visibility_code": "public"}
    ]
    assert "from source_post" in database_connection.executed_query
