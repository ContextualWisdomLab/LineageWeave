"""Naming and boundary contracts for the occupational catalog synchronizer."""

from __future__ import annotations

import ast
from pathlib import Path


SCRIPT_PATH = Path("scripts/sync_occupational_construct_catalog.py")


def test_catalog_sync_uses_semantic_owned_identifiers() -> None:
    """Keep command, database, payload, and result names domain-specific."""
    script_source = SCRIPT_PATH.read_text(encoding="utf-8")
    syntax_tree = ast.parse(script_source)
    owned_identifiers = {
        syntax_node.id
        for syntax_node in ast.walk(syntax_tree)
        if isinstance(syntax_node, ast.Name)
    }
    owned_identifiers.update(
        syntax_node.arg
        for syntax_node in ast.walk(syntax_tree)
        if isinstance(syntax_node, ast.arg)
    )
    owned_identifiers.update(
        syntax_node.name
        for syntax_node in ast.walk(syntax_tree)
        if isinstance(syntax_node, (ast.AsyncFunctionDef, ast.FunctionDef))
    )

    assert owned_identifiers.isdisjoint(
        {
            "_parser",
            "args",
            "conn",
            "count",
            "payload",
            "settings",
            "synchronize_catalog",
        }
    )
    assert {
        "_catalog_sync_parser",
        "catalog_payload",
        "command_arguments",
        "database_connection",
        "runtime_settings",
        "synchronize_occupational_construct_catalog",
        "synchronized_construct_count",
    } <= owned_identifiers


def test_catalog_sync_preserves_cli_and_output_contracts() -> None:
    """Keep the operator flag, release, and result keys at the boundary."""
    script_source = SCRIPT_PATH.read_text(encoding="utf-8")

    for contract_literal in (
        '"--target-dsn"',
        '"release"',
        '"31.0"',
        '"construct_count"',
    ):
        assert contract_literal in script_source
    assert (
        "asyncio.run(\n"
        "        synchronize_occupational_construct_catalog("
        in script_source
    )
