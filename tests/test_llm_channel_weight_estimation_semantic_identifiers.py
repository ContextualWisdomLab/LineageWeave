"""Naming and boundary contracts for queued LLM channel-weight estimation."""

from __future__ import annotations

import ast
from pathlib import Path


SCRIPT_PATH = Path("scripts/estimate_llm_channel_weights.py")
BEHAVIOR_TEST_PATH = Path("tests/test_estimate_llm_channel_weights_script.py")


def test_owned_llm_estimation_identifiers_are_semantic() -> None:
    """Require semantic identifiers throughout queued LLM estimation."""
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
            "_collect",
            "_submit",
            "args",
            "chosen",
            "collect",
            "conn",
            "estimate",
            "exc",
            "item",
            "name",
            "ordinal",
            "pairs",
            "parser",
            "polled",
            "result",
            "results",
            "retrieved",
            "row",
            "rows",
            "run",
            "score",
            "scores",
            "settings",
            "submit",
            "submitted",
            "subcommands",
            "unjudged",
            "updates",
        }
    )
    assert {
        "_collect_batch_estimation",
        "_submit_batch_estimation",
        "batch_result_record",
        "batch_result_records",
        "batch_results_payload",
        "batch_status_payload",
        "channel_weight_estimate",
        "chosen_pair_ordinals",
        "command_arguments",
        "database_connection",
        "estimation_run_record",
        "judgment_updates",
        "orchestrator_api_key",
        "orchestrator_base_url",
        "pair_judgment_records",
        "pair_ordinal",
        "runtime_settings",
        "source_post_rows",
    } <= owned_identifiers


def test_llm_provider_cli_json_and_persistence_contracts_are_unchanged() -> None:
    """Preserve LLM estimator boundary contracts."""
    script_source = SCRIPT_PATH.read_text(encoding="utf-8")

    for contract_literal in (
        '"custom_id"',
        '"mode"',
        '"messages"',
        '"role"',
        '"content"',
        '"job_id"',
        '"results"',
        '"status"',
        '"--post-limit"',
        '"--pair-limit"',
        '"--run-id"',
        '"estimation_run_id"',
        '"batch_job_id"',
        '"sampled_pair_count"',
        '"next_action"',
        "insert into lineage_weight_estimation_run",
        "insert into lineage_pair_judgment",
        "update lineage_pair_judgment",
        "update lineage_weight_estimation_run",
    ):
        assert contract_literal in script_source
    assert "asyncio.run(_submit_batch_estimation(command_arguments))" in script_source
    assert "asyncio.run(_collect_batch_estimation(command_arguments))" in script_source


def test_llm_estimator_behavior_tests_name_the_script_boundary() -> None:
    """Reject a generic alias for the queued-estimator module under test."""
    test_source = BEHAVIOR_TEST_PATH.read_text(encoding="utf-8")
    syntax_tree = ast.parse(test_source)
    owned_aliases = {
        imported_name.asname
        for syntax_node in ast.walk(syntax_tree)
        if isinstance(syntax_node, ast.Import)
        for imported_name in syntax_node.names
        if imported_name.asname
    }

    assert "script" not in owned_aliases
    assert "llm_estimation_script" in owned_aliases
