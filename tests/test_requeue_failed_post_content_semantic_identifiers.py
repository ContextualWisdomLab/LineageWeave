"""Naming and boundary contracts for explicit post-content requeue."""

from __future__ import annotations

import ast
from pathlib import Path


SCRIPT_PATH = Path("scripts/requeue_failed_post_content.py")


def test_post_content_requeue_uses_semantic_owned_identifiers() -> None:
    """Keep command, database, queue, request, and settings names specific."""
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
            "client",
            "connection",
            "parser",
            "request",
            "settings",
        }
    )
    assert {
        "_post_content_requeue_parser",
        "command_arguments",
        "command_parser",
        "database_connection",
        "post_content_job_request",
        "runtime_settings",
        "source_post_body_row",
        "valkey_client",
        "valkey_stream_entry_id",
    } <= owned_identifiers


def test_post_content_requeue_preserves_operator_and_resource_contracts() -> None:
    """Keep CLI, SQL, output, publication, and close behavior stable."""
    script_source = SCRIPT_PATH.read_text(encoding="utf-8")

    for contract_literal in (
        '"--post-id"',
        '"--target-dsn"',
        '"--valkey-url"',
        '"select post_body from source_post where post_id = $1::uuid"',
        '"post_id"',
        '"status"',
        '"published"',
        "requeue_failed_post_content_job(",
        "publish_post_content_event(",
        "await database_connection.close()",
        "await valkey_client.aclose()",
    ):
        assert contract_literal in script_source
    assert "asyncio.run(\n        requeue_post_content(" in script_source
