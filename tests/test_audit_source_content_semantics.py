import hashlib
import json

import pytest

from scripts.audit_source_content_semantics import (
    _parser,
    aggregate_results,
    parse_batch_result,
    selected_contents,
    validate_probability_sample_manifest,
)


def test_cli_defaults_to_the_internal_orchestrator_credential() -> None:
    """The audit must not send a provider credential to the internal service."""
    action = next(
        action
        for action in _parser()._actions
        if action.dest == "gateway_api_key_env"
    )

    assert action.default == "CONTEXTUAL_ORCHESTRATOR_TOKEN"


def _probability_manifest() -> dict[str, object]:
    """Return a synthetic, Rust-attested stratified sample contract."""
    digest = "a" * 64
    manifest: dict[str, object] = {
        "contract_kind": "lineageweave.semantic_coverage_probability_sample",
        "contract_version": 1,
        "population_size": 1000,
        "sample_size": 80,
        "design_code": "stratified_random_without_replacement",
        "target_confidence_level": "0.95",
        "target_margin_of_error": "0.05",
        "expected_proportion": "0.50",
        "expected_proportion_evidence_reference": "synthetic-prior-study:v1",
        "provider_failures_retained": True,
        "strata": [
            {
                "stratum_code": "synthetic-a",
                "population_size": 600,
                "sample_size": 48,
                "inclusion_probability": "0.08",
                "selection_frame_sha256": digest,
            },
            {
                "stratum_code": "synthetic-b",
                "population_size": 400,
                "sample_size": 32,
                "inclusion_probability": "0.08",
                "selection_frame_sha256": "b" * 64,
            },
        ],
        "selected_units": [
            {
                "ordinal": ordinal,
                "selection_token_sha256": hashlib.sha256(
                    f"synthetic-token-{ordinal}".encode()
                ).hexdigest(),
                "stratum_code": "synthetic-a" if ordinal < 48 else "synthetic-b",
            }
            for ordinal in range(80)
        ],
        "rust_owner_artifact": {
            "repository": "ContextualWisdomLab/fast-mlsirm",
            "artifact_version": "synthetic-test-v1",
            "formula_code": "nist_sematech_proportion_fpc_v1",
            "source_sha256": digest,
            "input_sha256": "",
            "output_sha256": "",
        },
    }
    artifact_input = {
        key: value
        for key, value in manifest.items()
        if key not in {"selected_units", "rust_owner_artifact"}
    }
    artifact = manifest["rust_owner_artifact"]
    assert isinstance(artifact, dict)
    artifact["input_sha256"] = hashlib.sha256(
        json.dumps(artifact_input, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    artifact["output_sha256"] = hashlib.sha256(
        json.dumps(
            manifest["selected_units"], sort_keys=True, separators=(",", ":")
        ).encode()
    ).hexdigest()
    return manifest


def test_parser_rejects_the_observed_100_to_60_cardinality_mismatch() -> None:
    payload = {
        "input_count": 60,
        "items": [
            {"item_index": index, "covered": True, "missing_semantic_dimensions": []}
            for index in range(60)
        ],
    }

    import json

    with pytest.raises(ValueError, match="input_count"):
        parse_batch_result(json.dumps(payload), expected_count=100)


def test_valid_batches_aggregate_without_source_values() -> None:
    rows = parse_batch_result(
        '{"input_count":2,"items":['
        '{"item_index":0,"covered":false,"missing_semantic_dimensions":["event_or_activity"]},'
        '{"item_index":1,"covered":true,"missing_semantic_dimensions":[]}]}',
        expected_count=2,
    )

    result = aggregate_results([rows], [4])

    assert result == {
        "complete": True,
        "sample_count": 2,
        "covered_count": 1,
        "uncovered_count": 1,
        "missing_semantic_dimension_counts": {"event_or_activity": 1},
        "batch_count": 1,
        "minimum_trace_step_count": 4,
        "maximum_trace_step_count": 4,
    }


def test_parser_rejects_ungoverned_dimensions() -> None:
    with pytest.raises(ValueError, match="ungoverned"):
        parse_batch_result(
            '{"input_count":1,"items":['
            '{"item_index":0,"covered":false,"missing_semantic_dimensions":["invented"]}]}',
            expected_count=1,
        )


def test_probability_sample_manifest_preserves_design_evidence() -> None:
    """The audit accepts only explicit probability and Rust-owner evidence."""
    manifest = _probability_manifest()
    artifact = manifest["rust_owner_artifact"]
    assert isinstance(artifact, dict)
    result, membership = validate_probability_sample_manifest(manifest, 80)

    assert result == {
        "design_code": "stratified_random_without_replacement",
        "population_size": 1000,
        "sample_size": 80,
        "target_confidence_level": "0.95",
        "target_margin_of_error": "0.05",
        "stratum_count": 2,
        "rust_owner_artifact_sha256": artifact["output_sha256"],
    }
    assert len(membership) == 80


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("design_code", "deterministic_windows", "probability design"),
        ("provider_failures_retained", False, "retain provider failures"),
        ("target_confidence_level", "95%", "decimal string"),
        ("expected_proportion_evidence_reference", "", "prior evidence"),
    ],
)
def test_probability_sample_manifest_rejects_noninferential_contracts(
    field: str, value: object, message: str
) -> None:
    """Deterministic windows and undocumented targets cannot imply corpus coverage."""
    manifest = _probability_manifest()
    manifest[field] = value

    with pytest.raises(ValueError, match=message):
        validate_probability_sample_manifest(manifest, 80)


def test_probability_sample_manifest_requires_known_stratum_inclusion_probability() -> (
    None
):
    """Every stratum retains a known inclusion probability and frame digest."""
    manifest = _probability_manifest()
    strata = manifest["strata"]
    assert isinstance(strata, list) and isinstance(strata[0], dict)
    strata[0]["inclusion_probability"] = "unknown"

    with pytest.raises(ValueError, match="known inclusion probability"):
        validate_probability_sample_manifest(manifest, 80)


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("population_size", 601, "stratum populations"),
        ("sample_size", 47, "stratum samples"),
    ],
)
def test_probability_manifest_stratum_totals_match_declared_totals(
    field: str, value: int, message: str
) -> None:
    """Stratum totals cannot contradict the declared sample population."""
    manifest = _probability_manifest()
    strata = manifest["strata"]
    assert isinstance(strata, list) and isinstance(strata[0], dict)
    strata[0][field] = value

    with pytest.raises(ValueError, match=message):
        validate_probability_sample_manifest(manifest, 80)


def test_probability_manifest_selected_units_match_each_stratum_sample() -> None:
    """Selected-unit membership must realize every declared stratum count."""
    manifest = _probability_manifest()
    selected_units = manifest["selected_units"]
    assert isinstance(selected_units, list) and isinstance(selected_units[0], dict)
    selected_units[0]["stratum_code"] = "synthetic-b"

    with pytest.raises(ValueError, match="selected-unit strata"):
        validate_probability_sample_manifest(manifest, 80)


def test_selected_contents_bind_query_order_to_owner_tokens() -> None:
    """A different query row cannot masquerade as the Rust-selected member."""
    token = "synthetic-owner-token"
    membership = ((hashlib.sha256(token.encode()).hexdigest(), "synthetic-a"),)

    assert selected_contents(
        [{"selection_token": token, "content_text": "Synthetic content"}], membership
    ) == ["Synthetic content"]
    with pytest.raises(ValueError, match="membership"):
        selected_contents(
            [{"selection_token": "replacement", "content_text": "Synthetic content"}],
            membership,
        )
