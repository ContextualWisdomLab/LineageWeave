import hashlib
import json
from copy import deepcopy
from dataclasses import asdict
from pathlib import Path

import pytest
from fast_mlsirm import SamplingStratum, finite_population_proportion_design

from scripts.audit_source_content_semantics import (
    _ontology_terms,
    _parser,
    aggregate_results,
    parse_batch_result,
    selected_contents,
    validate_probability_sample_manifest,
    validate_sampling_design_artifact,
)

_TERM_IRI = "https://example.test/ontology#Event"
_ALLOWED_TERMS = frozenset({_TERM_IRI})


def test_cli_defaults_to_the_internal_orchestrator_credential() -> None:
    """The audit must not send a provider credential to the internal service."""
    action = next(
        action
        for action in _parser()._actions
        if action.dest == "gateway_api_key_env"
    )

    assert action.default == "CONTEXTUAL_ORCHESTRATOR_TOKEN"
    design_action = next(
        action
        for action in _parser()._actions
        if action.dest == "sample_design_artifact_file"
    )
    assert design_action.required is True


def _probability_manifest() -> dict[str, object]:
    """Return a synthetic stratified sample-audit contract."""
    digest = "a" * 64
    manifest: dict[str, object] = {
        "contract_kind": "lineageweave.semantic_coverage_probability_sample",
        "contract_version": 2,
        "population_size": 1000,
        "sample_size": 80,
        "design_code": "stratified_random_without_replacement",
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
        "selection_manifest_sha256": "",
    }
    manifest["selection_manifest_sha256"] = hashlib.sha256(
        json.dumps(
            manifest["selected_units"], sort_keys=True, separators=(",", ":")
        ).encode()
    ).hexdigest()
    return manifest


def _rust_design_artifact() -> dict[str, object]:
    """Return the Rust-owned design matching the synthetic sample manifest."""
    design = finite_population_proportion_design(
        1000,
        0.95,
        0.1055,
        [SamplingStratum(600, 0.5), SamplingStratum(400, 0.5)],
        allocation_method="proportional",
    )
    return json.loads(json.dumps(asdict(design), sort_keys=True))


def test_parser_rejects_the_observed_100_to_60_cardinality_mismatch() -> None:
    payload = {
        "input_count": 60,
        "items": [
            {
                "item_index": index,
                "covered": True,
                "missing_semantic_dimensions": [],
                "supporting_term_iris": [_TERM_IRI],
            }
            for index in range(60)
        ],
    }

    import json

    with pytest.raises(ValueError, match="input_count"):
        parse_batch_result(json.dumps(payload), 100, _ALLOWED_TERMS)


def test_valid_batches_aggregate_without_source_values() -> None:
    rows = parse_batch_result(
        '{"input_count":2,"items":['
        '{"item_index":0,"covered":false,"missing_semantic_dimensions":["event_or_activity"],'
        '"supporting_term_iris":[]},'
        '{"item_index":1,"covered":true,"missing_semantic_dimensions":[],'
        f'"supporting_term_iris":["{_TERM_IRI}"]}}]}}',
        expected_count=2,
        allowed_term_iris=_ALLOWED_TERMS,
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
            '{"item_index":0,"covered":false,"missing_semantic_dimensions":["invented"],'
            '"supporting_term_iris":[]}]}',
            expected_count=1,
            allowed_term_iris=_ALLOWED_TERMS,
        )


@pytest.mark.parametrize(
    ("covered", "dimensions", "supporting_terms", "message"),
    [
        (True, [], [], "requires a supporting"),
        (False, [], [], "requires a missing"),
        (False, ["event_or_activity", "event_or_activity"], [], "duplicate missing"),
        (True, [], ["https://example.test/unknown"], "ungoverned supporting"),
    ],
)
def test_parser_requires_auditable_noncontradictory_verdicts(
    covered: bool,
    dimensions: list[str],
    supporting_terms: list[str],
    message: str,
) -> None:
    """Bare coverage and empty or duplicated gap verdicts fail closed."""
    payload = {
        "input_count": 1,
        "items": [
            {
                "item_index": 0,
                "covered": covered,
                "missing_semantic_dimensions": dimensions,
                "supporting_term_iris": supporting_terms,
            }
        ],
    }

    with pytest.raises(ValueError, match=message):
        parse_batch_result(json.dumps(payload), 1, _ALLOWED_TERMS)


def test_ontology_contract_contains_public_semantics_not_only_local_names() -> None:
    """Coverage decisions receive term kinds and meaning-bearing RDF relations."""
    terms = _ontology_terms(Path("docs/ontology/lineageweave-kg.ttl"))

    assert terms
    assert all(term["iri"] and term["kinds"] for term in terms)
    assert any(term["labels"] for term in terms)
    assert any(term["domains"] or term["ranges"] for term in terms)
    by_iri = {term["iri"]: term for term in terms}
    namespace = "https://contextualwisdomlab.github.io/LineageWeave/ontology#"
    assert "http://www.w3.org/ns/prov#Entity" in by_iri[namespace + "Post"]["superclasses"]
    assert "http://www.w3.org/ns/prov#Person" in by_iri[namespace + "Person"]["superclasses"]
    assert "http://www.w3.org/ns/prov#wasDerivedFrom" in by_iri[
        namespace + "wasDerivedFromPost"
    ]["superproperties"]


def test_probability_sample_manifest_preserves_design_evidence() -> None:
    """The audit preserves selection evidence without claiming corpus inference."""
    manifest = _probability_manifest()
    result, membership = validate_probability_sample_manifest(manifest, 80)

    assert result == {
        "design_code": "stratified_random_without_replacement",
        "population_size": 1000,
        "sample_size": 80,
        "stratum_count": 2,
        "selection_manifest_sha256": manifest["selection_manifest_sha256"],
        "corpus_inference_available": False,
    }
    assert len(membership) == 80


def test_rust_sampling_design_replays_and_binds_the_manifest() -> None:
    """Caller hashes cannot replace exact package-owned Rust replay evidence."""
    manifest = _probability_manifest()
    artifact = _rust_design_artifact()

    result = validate_sampling_design_artifact(artifact, manifest)

    assert result["sampling_design_verified"] is True
    assert result["corpus_inference_available"] is False
    assert result["artifact_sha256"] == artifact["artifact_sha256"]
    artifact["sample_size"] = 79
    with pytest.raises(ValueError, match="Rust replay"):
        validate_sampling_design_artifact(artifact, manifest)


def test_rust_sampling_design_rejects_every_unbound_boundary() -> None:
    """Malformed, unreplayable, or manifest-divergent artifacts fail closed."""
    manifest = _probability_manifest()
    artifact = _rust_design_artifact()

    wrong_fields = deepcopy(artifact)
    wrong_fields.pop("source_sha256")
    with pytest.raises(ValueError, match="fields"):
        validate_sampling_design_artifact(wrong_fields, manifest)

    no_strata = deepcopy(artifact)
    no_strata["strata"] = []
    with pytest.raises(ValueError, match="ordered strata"):
        validate_sampling_design_artifact(no_strata, manifest)

    malformed_stratum = deepcopy(artifact)
    malformed_stratum["strata"][0]["unsupported"] = True
    with pytest.raises(ValueError, match="strata are invalid"):
        validate_sampling_design_artifact(malformed_stratum, manifest)

    unreplayable = deepcopy(artifact)
    unreplayable["allocation_method"] = "caller_guess"
    with pytest.raises(ValueError, match="cannot be replayed"):
        validate_sampling_design_artifact(unreplayable, manifest)

    missing_manifest_strata = deepcopy(manifest)
    missing_manifest_strata["strata"] = None
    with pytest.raises(TypeError, match="strata are unavailable"):
        validate_sampling_design_artifact(artifact, missing_manifest_strata)

    wrong_total = deepcopy(manifest)
    wrong_total["sample_size"] = 79
    with pytest.raises(ValueError, match="totals"):
        validate_sampling_design_artifact(artifact, wrong_total)

    wrong_allocation = deepcopy(manifest)
    wrong_allocation["strata"][0]["sample_size"] = 47
    wrong_allocation["strata"][1]["sample_size"] = 33
    with pytest.raises(ValueError, match="allocation"):
        validate_sampling_design_artifact(artifact, wrong_allocation)


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("design_code", "deterministic_windows", "probability design"),
        ("provider_failures_retained", False, "retain provider failures"),
        ("contract_version", 1, "unsupported"),
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


def test_probability_manifest_inclusion_probability_matches_sampling_fraction() -> None:
    """A declared probability cannot contradict the selected stratum fraction."""
    manifest = _probability_manifest()
    strata = manifest["strata"]
    assert isinstance(strata, list) and isinstance(strata[0], dict)
    strata[0]["inclusion_probability"] = "0.5"

    with pytest.raises(ValueError, match="sampling fraction"):
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
