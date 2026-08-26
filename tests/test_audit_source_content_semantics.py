import hashlib
import json
from pathlib import Path

import pytest

from scripts.audit_source_content_semantics import (
    _ontology_terms,
    _parser,
    _prompt,
    aggregate_results,
    parse_batch_result,
    selected_contents,
    validate_probability_sample_manifest,
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


def test_audit_contract_distinguishes_instance_data_from_schema_gaps() -> None:
    """Private names and values do not require private ontology vocabulary."""
    prompt = _prompt([], ["Synthetic event at a synthetic facility"])

    assert "as instance data, not missing schema terms" in prompt
    assert "no supplied class/property can represent it" in prompt


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
    assert by_iri["http://www.w3.org/ns/prov#Activity"]["kinds"] == [
        "http://www.w3.org/2002/07/owl#Class"
    ]
    assert by_iri["http://www.w3.org/ns/prov#wasInformedBy"]["qualification"] == {
        "qualification_relation": "http://www.w3.org/ns/prov#qualifiedCommunication",
        "influence_class": "http://www.w3.org/ns/prov#Communication",
        "influencer_relation": "http://www.w3.org/ns/prov#activity",
    }


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
