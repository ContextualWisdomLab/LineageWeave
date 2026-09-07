"""Naming and boundary contracts for deterministic channel-weight estimation."""

from __future__ import annotations

import ast
from pathlib import Path


SCRIPT_PATH = Path("scripts/estimate_channel_weights.py")


def _function_identifiers(function_name: str) -> set[str]:
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
