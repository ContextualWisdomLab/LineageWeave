"""Contract tests for the future Naruon-facing LineageWeave boundary."""

from __future__ import annotations

import json
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path

import pytest

from lineageweave.external_lineage_contract import (
    CONTRACT_VERSION,
    ChannelEvidence,
    ExplicitParent,
    LineageAnalysisResult,
    LineageContractError,
    LineageEdgeResult,
    LineageLimitation,
    ProjectProjection,
    parse_lineage_analysis_request,
    request_digest,
    result_digest,
    serialize_lineage_analysis_request,
    serialize_lineage_analysis_result,
)

_ROOT = Path(__file__).resolve().parents[1]


def _record(
    evidence_ref: str,
    *,
    occurred_at: str = "2026-08-20T09:00:00Z",
    available_at: str = "2026-08-20T09:01:00Z",
    explicit_parent: dict[str, str] | None = None,
) -> dict[str, object]:
    return {
        "evidence_ref": evidence_ref,
        "group_ref": "workspace:demo",
        "source_kind_code": "email",
        "truth_status_code": "observed",
        "label": f"Subject {evidence_ref}",
        "occurred_at": occurred_at,
        "available_at": available_at,
        "secondary_key": "provider-thread:opaque",
        "project_ref": "project:opaque",
        "explicit_parent": explicit_parent,
    }


def _payload() -> dict[str, object]:
    return {
        "contract_version": "1.0.0",
        "analysis_id": "analysis:demo-001",
        "analysis_scope_code": "email_lineage",
        "knowledge_cutoff": "2026-08-20T18:00:00+09:00",
        "policy": {
            "candidate_window": 50,
            "maximum_pair_evaluations": 1000,
            "minimum_fused_score": 0.3,
            "allow_llm": False,
        },
        "records": [
            _record("email:001"),
            _record(
                "email:002",
                occurred_at="2026-08-20T09:05:00Z",
                available_at="2026-08-20T09:06:00Z",
                explicit_parent={
                    "evidence_ref": "email:001",
                    "relation_code": "rfc_reply",
                },
            ),
        ],
    }


def _result_fixture() -> LineageAnalysisResult:
    return LineageAnalysisResult(
        contract_version=CONTRACT_VERSION,
        analysis_id="analysis:fixture",
        analysis_scope_code="generic_lineage",
        knowledge_cutoff=None,
        included_evidence_refs=("record:001",),
        excluded_evidence_refs=(),
        llm_status_code="not_requested",
        edges=(),
        project_projections=(),
        limitations=(),
        result_digest="",
    )


def test_parse_request_is_strict_immutable_and_canonicalizes_timestamps() -> None:
    request = parse_lineage_analysis_request(_payload())

    assert request.contract_version == CONTRACT_VERSION
    assert request.analysis_id == "analysis:demo-001"
    assert request.analysis_scope_code == "email_lineage"
    assert request.knowledge_cutoff == datetime(
        2026,
        8,
        20,
        9,
        0,
        tzinfo=timezone.utc,
    )
    assert request.records[1].explicit_parent == ExplicitParent(
        evidence_ref="email:001",
        relation_code="rfc_reply",
    )
    assert serialize_lineage_analysis_request(request)[
        "knowledge_cutoff"
    ] == "2026-08-20T09:00:00Z"
    with pytest.raises(AttributeError):
        request.analysis_id = "changed"  # type: ignore[misc]


def test_request_digest_is_stable_when_keys_and_records_are_reordered() -> None:
    payload = _payload()
    reordered = {
        "records": list(reversed(payload["records"])),  # type: ignore[arg-type]
        "policy": {
            "allow_llm": False,
            "minimum_fused_score": 0.3,
            "maximum_pair_evaluations": 1000,
            "candidate_window": 50,
        },
        "knowledge_cutoff": payload["knowledge_cutoff"],
        "analysis_scope_code": payload["analysis_scope_code"],
        "analysis_id": payload["analysis_id"],
        "contract_version": payload["contract_version"],
    }

    assert request_digest(
        parse_lineage_analysis_request(payload)
    ) == request_digest(parse_lineage_analysis_request(reordered))


@pytest.mark.parametrize(
    ("mutator", "expected_code"),
    [
        (lambda payload: payload.update({"unexpected": True}), "unknown_field"),
        (
            lambda payload: payload["policy"].update(  # type: ignore[union-attr]
                {"unexpected": True}
            ),
            "unknown_field",
        ),
        (
            lambda payload: payload["records"][0].update(  # type: ignore[index,union-attr]
                {"unexpected": True}
            ),
            "unknown_field",
        ),
        (
            lambda payload: payload.update({"contract_version": "2.0.0"}),
            "unsupported_contract_version",
        ),
        (
            lambda payload: payload.update(
                {"analysis_scope_code": "mailbox_dump"}
            ),
            "unknown_analysis_scope",
        ),
    ],
)
def test_parser_rejects_unknown_fields_and_vocabularies(
    mutator,
    expected_code: str,
) -> None:
    payload = _payload()
    mutator(payload)

    with pytest.raises(LineageContractError) as captured:
        parse_lineage_analysis_request(payload)

    assert captured.value.code == expected_code


def test_parser_rejects_duplicate_references_and_record_count_bounds() -> None:
    payload = _payload()
    payload["records"] = [_record("email:001"), _record("email:001")]
    with pytest.raises(LineageContractError) as duplicate:
        parse_lineage_analysis_request(payload)
    assert duplicate.value.code == "duplicate_evidence_ref"

    payload["records"] = []
    with pytest.raises(LineageContractError) as empty:
        parse_lineage_analysis_request(payload)
    assert empty.value.code == "record_count_out_of_bounds"

    payload["records"] = [
        _record(f"email:{index:03d}")
        for index in range(501)
    ]
    with pytest.raises(LineageContractError) as oversized:
        parse_lineage_analysis_request(payload)
    assert oversized.value.code == "record_count_out_of_bounds"


@pytest.mark.parametrize(
    ("field_name", "value", "expected_code"),
    [
        (
            "occurred_at",
            "2026-08-20T09:00:00",
            "timestamp_must_be_offset_aware",
        ),
        ("available_at", "not-a-time", "invalid_timestamp"),
        (
            "evidence_ref",
            "https://mail.example/message/1",
            "unsafe_opaque_reference",
        ),
        ("evidence_ref", "contains whitespace", "unsafe_opaque_reference"),
        ("label", "", "text_length_out_of_bounds"),
        ("label", "x" * 2001, "text_length_out_of_bounds"),
    ],
)
def test_parser_rejects_unsafe_identifiers_timestamps_and_text(
    field_name: str,
    value: str,
    expected_code: str,
) -> None:
    payload = _payload()
    payload["records"][0][field_name] = value  # type: ignore[index]

    with pytest.raises(LineageContractError) as captured:
        parse_lineage_analysis_request(payload)

    assert captured.value.code == expected_code


@pytest.mark.parametrize(
    ("field_name", "value", "expected_code"),
    [
        ("candidate_window", 0, "policy_value_out_of_bounds"),
        ("candidate_window", 201, "policy_value_out_of_bounds"),
        ("maximum_pair_evaluations", 0, "policy_value_out_of_bounds"),
        ("maximum_pair_evaluations", 5_001, "policy_value_out_of_bounds"),
        ("minimum_fused_score", -0.1, "policy_value_out_of_bounds"),
        ("minimum_fused_score", 1.1, "policy_value_out_of_bounds"),
        ("allow_llm", "yes", "invalid_field_type"),
    ],
)
def test_parser_rejects_invalid_policy_values(
    field_name: str,
    value: object,
    expected_code: str,
) -> None:
    payload = _payload()
    payload["policy"][field_name] = value  # type: ignore[index]

    with pytest.raises(LineageContractError) as captured:
        parse_lineage_analysis_request(payload)

    assert captured.value.code == expected_code


def test_result_serialization_is_deterministic_and_digest_is_external() -> None:
    edge = LineageEdgeResult(
        parent_evidence_ref="email:001",
        child_evidence_ref="email:002",
        relation_type_code="reconstructed_continuation",
        truth_status_code="inferred",
        fused_score=0.75,
        channel_evidence=(
            ChannelEvidence("text", 0.8, 0.5, 0.4),
            ChannelEvidence("temporal", 0.7, 0.5, 0.35),
        ),
    )
    result = LineageAnalysisResult(
        contract_version=CONTRACT_VERSION,
        analysis_id="analysis:demo-001",
        analysis_scope_code="email_lineage",
        knowledge_cutoff=datetime(
            2026,
            8,
            20,
            9,
            0,
            tzinfo=timezone.utc,
        ),
        included_evidence_refs=("email:001", "email:002"),
        excluded_evidence_refs=(),
        llm_status_code="not_requested",
        edges=(edge,),
        project_projections=(
            ProjectProjection(
                "workspace:demo",
                "project:opaque",
                ("email:001", "email:002"),
                "proposed",
            ),
        ),
        limitations=(
            LineageLimitation("none", None, "No material limitation."),
        ),
        result_digest="",
    )
    digest = result_digest(result)
    finalized = replace(result, result_digest=digest)

    serialized = serialize_lineage_analysis_result(finalized)
    assert serialized["result_digest"] == digest
    assert serialized["knowledge_cutoff"] == "2026-08-20T09:00:00Z"
    assert result_digest(finalized) == digest
    assert json.dumps(serialized, sort_keys=True, separators=(",", ":"))


def test_public_schema_exists_and_mirrors_contract_vocabularies() -> None:
    schema = json.loads(
        (
            _ROOT
            / "docs"
            / "contracts"
            / "external-lineage-analysis-v1.schema.json"
        ).read_text(encoding="utf-8")
    )

    assert schema["$schema"] == (
        "https://json-schema.org/draft/2020-12/schema"
    )
    assert schema["properties"]["contract_version"]["const"] == (
        CONTRACT_VERSION
    )
    assert set(
        schema["properties"]["analysis_scope_code"]["enum"]
    ) == {
        "email_lineage",
        "project_history",
        "generic_lineage",
    }
    assert schema["additionalProperties"] is False
    pair_budget = schema["$defs"]["LineageAnalysisPolicy"][
        "properties"
    ]["maximum_pair_evaluations"]
    assert pair_budget == {
        "type": "integer",
        "minimum": 1,
        "maximum": 5000,
    }


def test_parser_rejects_non_object_and_missing_required_field() -> None:
    with pytest.raises(LineageContractError) as non_object:
        parse_lineage_analysis_request([])
    assert non_object.value.code == "invalid_field_type"

    payload = _payload()
    del payload["analysis_id"]
    with pytest.raises(LineageContractError) as missing:
        parse_lineage_analysis_request(payload)
    assert missing.value.code == "missing_field"


def test_parser_rejects_wrong_scalar_types_and_non_array_records() -> None:
    mutations = [
        ("contract_version", 1, "invalid_field_type"),
        ("knowledge_cutoff", 1, "invalid_field_type"),
        ("analysis_scope_code", 1, "invalid_field_type"),
    ]
    for field, value, expected in mutations:
        payload = _payload()
        payload[field] = value
        with pytest.raises(LineageContractError) as captured:
            parse_lineage_analysis_request(payload)
        assert captured.value.code == expected

    payload = _payload()
    payload["policy"]["minimum_fused_score"] = "0.3"  # type: ignore[index]
    with pytest.raises(LineageContractError) as number:
        parse_lineage_analysis_request(payload)
    assert number.value.code == "invalid_field_type"

    payload = _payload()
    payload["policy"]["candidate_window"] = 50.0  # type: ignore[index]
    with pytest.raises(LineageContractError) as integer:
        parse_lineage_analysis_request(payload)
    assert integer.value.code == "invalid_field_type"

    payload = _payload()
    payload["records"] = tuple(payload["records"])  # type: ignore[arg-type]
    with pytest.raises(LineageContractError) as records:
        parse_lineage_analysis_request(payload)
    assert records.value.code == "invalid_field_type"


def test_optional_references_may_be_omitted() -> None:
    payload = _payload()
    record = payload["records"][0]  # type: ignore[index]
    del record["secondary_key"]
    del record["project_ref"]
    del record["explicit_parent"]

    parsed = parse_lineage_analysis_request(payload)

    assert parsed.records[0].secondary_key is None
    assert parsed.records[0].project_ref is None
    assert parsed.records[0].explicit_parent is None


def test_result_serializer_rejects_naive_timestamp_and_invalid_scores() -> None:
    result = replace(
        _result_fixture(),
        knowledge_cutoff=datetime(2026, 8, 20, 9, 0),
    )
    with pytest.raises(LineageContractError) as naive:
        serialize_lineage_analysis_result(result)
    assert naive.value.code == "timestamp_must_be_offset_aware"

    invalid_type_edge = LineageEdgeResult(
        "record:001",
        "record:002",
        "reconstructed_continuation",
        "inferred",
        True,  # type: ignore[arg-type]
        (ChannelEvidence("text", 0.5, 1.0, 0.5),),
    )
    result_with_two_records = replace(
        _result_fixture(),
        included_evidence_refs=("record:001", "record:002"),
    )
    with pytest.raises(LineageContractError) as score_type:
        serialize_lineage_analysis_result(
            replace(
                result_with_two_records,
                edges=(invalid_type_edge,),
            )
        )
    assert score_type.value.code == "invalid_field_type"

    invalid_range_edge = replace(invalid_type_edge, fused_score=1.1)
    with pytest.raises(LineageContractError) as score_range:
        serialize_lineage_analysis_result(
            replace(
                result_with_two_records,
                edges=(invalid_range_edge,),
            )
        )
    assert score_range.value.code == "score_out_of_bounds"


def test_result_serializer_rejects_non_proposed_project_and_wrong_version() -> None:
    project = ProjectProjection(
        "workspace:one",
        "project:one",
        ("record:001",),
        "observed",
    )  # type: ignore[arg-type]
    with pytest.raises(LineageContractError) as truth:
        serialize_lineage_analysis_result(
            replace(
                _result_fixture(),
                project_projections=(project,),
            )
        )
    assert truth.value.code == "unknown_result_truth_status"

    with pytest.raises(LineageContractError) as version:
        serialize_lineage_analysis_result(
            replace(_result_fixture(), contract_version="2.0.0")
        )
    assert version.value.code == "unsupported_contract_version"


def test_result_requires_a_valid_digest_for_transport() -> None:
    with pytest.raises(LineageContractError) as captured:
        serialize_lineage_analysis_result(_result_fixture())

    assert captured.value.code == "invalid_result_digest"


def test_result_rejects_overlapping_or_duplicate_partitions() -> None:
    overlap = replace(
        _result_fixture(),
        included_evidence_refs=("record:001",),
        excluded_evidence_refs=("record:001",),
        result_digest="sha256:" + "0" * 64,
    )
    with pytest.raises(LineageContractError) as captured:
        serialize_lineage_analysis_result(overlap)
    assert captured.value.code == "evidence_partition_overlap"

    duplicate = replace(
        _result_fixture(),
        included_evidence_refs=("record:001", "record:001"),
        result_digest="sha256:" + "0" * 64,
    )
    with pytest.raises(LineageContractError) as duplicate_error:
        serialize_lineage_analysis_result(duplicate)
    assert duplicate_error.value.code == "duplicate_evidence_ref"


def test_result_rejects_unincluded_edge_or_project_references() -> None:
    edge = LineageEdgeResult(
        "record:001",
        "record:missing",
        "reconstructed_continuation",
        "inferred",
        0.5,
        (ChannelEvidence("text", 0.5, 1.0, 0.5),),
    )
    result = replace(
        _result_fixture(),
        edges=(edge,),
        result_digest="sha256:" + "0" * 64,
    )
    with pytest.raises(LineageContractError) as edge_error:
        serialize_lineage_analysis_result(result)
    assert edge_error.value.code == "edge_reference_not_included"

    project = ProjectProjection(
        "workspace:one",
        "project:one",
        ("record:missing",),
        "proposed",
    )
    result = replace(
        _result_fixture(),
        project_projections=(project,),
        result_digest="sha256:" + "0" * 64,
    )
    with pytest.raises(LineageContractError) as project_error:
        serialize_lineage_analysis_result(result)
    assert project_error.value.code == "project_reference_not_included"


def test_result_rejects_self_edges_and_channel_math_errors() -> None:
    base = replace(
        _result_fixture(),
        included_evidence_refs=("record:001", "record:002"),
    )
    self_edge = LineageEdgeResult(
        "record:001",
        "record:001",
        "reconstructed_continuation",
        "inferred",
        0.5,
        (ChannelEvidence("text", 0.5, 1.0, 0.5),),
    )
    with pytest.raises(LineageContractError) as self_error:
        serialize_lineage_analysis_result(
            replace(
                base,
                edges=(self_edge,),
                result_digest="sha256:" + "0" * 64,
            )
        )
    assert self_error.value.code == "self_lineage_edge"

    duplicate_channels = replace(
        self_edge,
        parent_evidence_ref="record:002",
        channel_evidence=(
            ChannelEvidence("text", 0.5, 0.5, 0.25),
            ChannelEvidence("text", 0.5, 0.5, 0.25),
        ),
    )
    with pytest.raises(LineageContractError) as duplicate_error:
        serialize_lineage_analysis_result(
            replace(
                base,
                edges=(duplicate_channels,),
                result_digest="sha256:" + "0" * 64,
            )
        )
    assert duplicate_error.value.code == "duplicate_channel_code"

    bad_weights = replace(
        duplicate_channels,
        channel_evidence=(
            ChannelEvidence("text", 0.5, 0.4, 0.2),
            ChannelEvidence("temporal", 0.5, 0.4, 0.2),
        ),
    )
    with pytest.raises(LineageContractError) as weight_error:
        serialize_lineage_analysis_result(
            replace(
                base,
                edges=(bad_weights,),
                result_digest="sha256:" + "0" * 64,
            )
        )
    assert weight_error.value.code == "channel_weight_sum_mismatch"

    bad_contribution = replace(
        bad_weights,
        channel_evidence=(
            ChannelEvidence("text", 0.5, 0.5, 0.2),
            ChannelEvidence("temporal", 0.5, 0.5, 0.2),
        ),
    )
    with pytest.raises(LineageContractError) as contribution_error:
        serialize_lineage_analysis_result(
            replace(
                base,
                edges=(bad_contribution,),
                result_digest="sha256:" + "0" * 64,
            )
        )
    assert contribution_error.value.code == (
        "channel_contribution_mismatch"
    )


def test_result_rejects_unsafe_analysis_identifier() -> None:
    result = replace(
        _result_fixture(),
        analysis_id="https://unsafe.example/run",
        result_digest="sha256:" + "0" * 64,
    )
    with pytest.raises(LineageContractError) as captured:
        serialize_lineage_analysis_result(result)
    assert captured.value.code == "unsafe_opaque_reference"


def test_result_rejects_missing_channels_and_contribution_mismatch() -> None:
    base = replace(
        _result_fixture(),
        included_evidence_refs=("record:001", "record:002"),
    )
    missing_channels = LineageEdgeResult(
        "record:001",
        "record:002",
        "reconstructed_continuation",
        "inferred",
        0.5,
        (),
    )
    with pytest.raises(LineageContractError) as missing:
        serialize_lineage_analysis_result(
            replace(
                base,
                edges=(missing_channels,),
                result_digest="sha256:" + "0" * 64,
            )
        )
    assert missing.value.code == "missing_channel_evidence"

    inconsistent = replace(
        missing_channels,
        channel_evidence=(
            ChannelEvidence("text", 0.5, 0.5, 0.3),
            ChannelEvidence("temporal", 0.5, 0.5, 0.2),
        ),
    )
    with pytest.raises(LineageContractError) as mismatch:
        serialize_lineage_analysis_result(
            replace(
                base,
                edges=(inconsistent,),
                result_digest="sha256:" + "0" * 64,
            )
        )
    assert mismatch.value.code == "channel_contribution_mismatch"


def test_result_rejects_channel_sum_that_does_not_equal_fused_score() -> None:
    """The fused score must reconcile with all otherwise valid contributions."""

    edge = LineageEdgeResult(
        "record:001",
        "record:002",
        "reconstructed_continuation",
        "inferred",
        0.5,
        (
            ChannelEvidence("text", 0.2, 0.5, 0.1),
            ChannelEvidence("temporal", 0.2, 0.5, 0.1),
        ),
    )
    with pytest.raises(LineageContractError) as captured:
        serialize_lineage_analysis_result(
            replace(
                _result_fixture(),
                included_evidence_refs=("record:001", "record:002"),
                edges=(edge,),
                result_digest="sha256:" + "0" * 64,
            )
        )

    assert captured.value.code == "channel_contribution_mismatch"


def test_result_rejects_duplicate_project_evidence_references() -> None:
    project = ProjectProjection(
        "workspace:one",
        "project:one",
        ("record:001", "record:001"),
        "proposed",
    )
    with pytest.raises(LineageContractError) as captured:
        serialize_lineage_analysis_result(
            replace(
                _result_fixture(),
                project_projections=(project,),
                result_digest="sha256:" + "0" * 64,
            )
        )
    assert captured.value.code == "duplicate_evidence_ref"


def test_result_rejects_digest_not_matching_canonical_content() -> None:
    result = replace(
        _result_fixture(),
        result_digest="sha256:" + "0" * 64,
    )

    with pytest.raises(LineageContractError) as captured:
        serialize_lineage_analysis_result(result)

    assert captured.value.code == "result_digest_mismatch"
