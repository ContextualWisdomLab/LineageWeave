"""Naming and boundary contracts for deterministic channel-weight estimation."""

from __future__ import annotations

import ast
from pathlib import Path

SCRIPT_PATH = Path("scripts/estimate_channel_weights.py")
BEHAVIOR_TEST_PATH = Path("tests/test_estimate_channel_weights_script.py")


def _function_identifiers(function_name: str) -> set[str]:
    """Collect identifiers owned by the target estimator function."""
    source_tree = ast.parse(SCRIPT_PATH.read_text(encoding="utf-8"))
    function_node = next(
        node
        for node in ast.walk(source_tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and node.name == function_name
    )
    return {
        identifier
        for node in ast.walk(function_node)
        for identifier in (
            [node.id]
            if isinstance(node, ast.Name)
            else [node.arg]
            if isinstance(node, ast.arg)
            else []
        )
    }


def test_owned_estimation_identifiers_are_semantic() -> None:
    """Require semantic identifiers throughout deterministic estimation."""
    expected_identifiers = {
        "source_snapshot_digest": {
            "source_post_rows",
            "source_post_row",
            "digest_material",
        },
        "sample_pair_scores": {
            "lineage_records",
            "candidate_window",
            "channel_groups",
            "lineage_record",
            "ordered_records",
            "candidate_record",
        },
        "subsample_stride": {
            "sample_pair_total",
            "sample_pair_limit",
            "sample_stride",
        },
        "persist_estimate": {
            "database_connection",
            "channel_weight_estimate",
            "installed_estimator_version",
            "channel_code",
            "weight_value",
        },
        "_run_channel_weight_estimation": {
            "command_arguments",
            "runtime_settings",
            "database_connection",
            "source_post_rows",
            "lineage_records",
            "channel_weight_estimate",
        },
    }
    forbidden_identifiers = {
        "args",
        "candidate",
        "channel",
        "conn",
        "estimate",
        "groups",
        "limit",
        "material",
        "record",
        "records",
        "row",
        "rows",
        "settings",
        "stride",
        "total",
        "version",
        "weight",
        "window",
    }

    for function_name, required_identifiers in expected_identifiers.items():
        function_identifiers = _function_identifiers(function_name)
        assert required_identifiers <= function_identifiers
        assert function_identifiers.isdisjoint(forbidden_identifiers)


def test_external_cli_json_and_persistence_contracts_are_unchanged() -> None:
    """Preserve deterministic estimator boundary contracts."""
    script_source = SCRIPT_PATH.read_text(encoding="utf-8")

    assert '"--post-limit"' in script_source
    assert '"--dry-run"' in script_source
    for result_key in (
        "weights",
        "channel_set_code",
        "sample_pair_count",
        "estimation_method_code",
        "anchor_method_code",
        "estimation_run_id",
        "source_snapshot_sha256",
        "knowledge_cutoff",
        "persisted",
        "activation",
    ):
        assert f'"{result_key}"' in script_source
    assert "insert into lineage_channel_weight" in script_source
    assert (
        "delete from lineage_channel_weight where channel_set_code = $1"
        in script_source
    )
    assert (
        "asyncio.run(_run_channel_weight_estimation(command_arguments))"
        in script_source
    )


def test_estimator_behavior_tests_use_domain_specific_fixture_names() -> None:
    """Keep owned deterministic-estimator test identifiers semantic."""
    test_source = BEHAVIOR_TEST_PATH.read_text(encoding="utf-8")
    syntax_tree = ast.parse(test_source)
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
        if isinstance(
            syntax_node,
            (ast.AsyncFunctionDef, ast.ClassDef, ast.FunctionDef),
        )
    )
    owned_identifiers.update(
        syntax_node.attr
        for syntax_node in ast.walk(syntax_tree)
        if isinstance(syntax_node, ast.Attribute)
    )

    assert owned_identifiers.isdisjoint(
        {
            "_Connection",
            "_record",
            "chosen",
            "executed",
            "first",
            "group",
            "inserted",
            "minute",
            "script",
            "secondary",
        }
    )
    assert {
        "_EstimationDatabaseConnection",
        "_source_post_record",
        "channel_weight_script",
        "chosen_indexes",
        "executed_queries",
        "first_digest",
        "inserted_rows",
        "minute_offset",
        "secondary_grouping_key",
        "thread_group_key",
    } <= owned_identifiers
