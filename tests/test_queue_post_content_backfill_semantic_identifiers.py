"""Naming and boundary contracts for the post-content queue backfill."""

from __future__ import annotations

import ast
from pathlib import Path


SCRIPT_PATH = Path("scripts/queue_post_content_backfill.py")


def test_queue_backfill_uses_semantic_owned_identifiers() -> None:
    """Keep command, database, queue, record, and result names specific."""
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
            "complete",
            "connection",
            "limit",
            "parser",
            "request",
            "result",
            "row",
            "rows",
            "settings",
        }
    )
    assert {
        "_queue_backfill_parser",
        "backfill_summary",
        "command_arguments",
        "database_connection",
        "post_limit",
        "post_content_complete",
        "post_content_job_request",
        "runtime_settings",
        "source_post_record",
        "source_post_records",
        "valkey_client",
    } <= owned_identifiers


def test_queue_backfill_preserves_cli_result_sql_and_publish_contracts() -> None:
    """Keep public operator inputs, outputs, persistence, and event calls stable."""
    script_source = SCRIPT_PATH.read_text(encoding="utf-8")

    for contract_literal in (
        '"--target-dsn"',
        '"--valkey-url"',
        '"--limit"',
        '"--all"',
        '"scanned_posts"',
        '"already_complete"',
        '"queued_posts"',
        '"published_events"',
        "from source_post",
        "post_content_unit",
        "post_content_embedding",
        "post_content_image_region_embedding",
        "ensure_post_content_job(",
        "publish_post_content_event(",
    ):
        assert contract_literal in script_source
    assert "asyncio.run(\n        queue_post_content_backfill(" in script_source
