"""Audit private source content against the ontology without emitting source text."""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import multiprocessing
import os
import re
import tempfile
from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import asdict
from pathlib import Path
from typing import Any, cast

import asyncpg
from rdflib import Graph, URIRef
from rdflib.namespace import OWL, RDF, RDFS, SKOS

from lineageweave.http_client import chat_completion_content, post_json
from lineageweave.prov_o import (
    PROV,
    PROV_CLASSES,
    PROV_QUALIFICATIONS,
    PROV_RELATIONS,
    ProvGraph,
)

SEMANTIC_DIMENSIONS = frozenset(
    {
        "event_or_activity",
        "location_or_geography",
        "product_or_service",
        "project_or_initiative",
        "facility_asset_or_equipment",
        "topic_or_domain",
        "status_or_stage",
        "time_interval_or_deadline",
        "organization_role",
        "person_or_actor",
        "communication_or_document_type",
        "commercial_transaction",
        "quantity_or_measurement",
        "requirement_issue_or_risk",
        "other_unmodeled_meaning",
    }
)
_ONTOLOGY_NAMESPACE = "https://contextualwisdomlab.github.io/LineageWeave/ontology#"
SEMANTIC_DIMENSION_TERM_IRIS: Mapping[str, tuple[str, ...]] = {
    "event_or_activity": (
        _ONTOLOGY_NAMESPACE + "BusinessEventActivity",
        _ONTOLOGY_NAMESPACE + "describesActivity",
        str(PROV.Activity),
    ),
    "location_or_geography": (
        _ONTOLOGY_NAMESPACE + "Location",
        _ONTOLOGY_NAMESPACE + "concernsLocation",
        str(PROV.Location),
    ),
    "product_or_service": (
        _ONTOLOGY_NAMESPACE + "ProductOrService",
        _ONTOLOGY_NAMESPACE + "concernsProductOrService",
    ),
    "project_or_initiative": (
        _ONTOLOGY_NAMESPACE + "Project",
        _ONTOLOGY_NAMESPACE + "mentionsProject",
    ),
    "facility_asset_or_equipment": (
        _ONTOLOGY_NAMESPACE + "FacilityAssetEquipment",
        _ONTOLOGY_NAMESPACE + "concernsFacilityAssetEquipment",
    ),
    "topic_or_domain": (
        _ONTOLOGY_NAMESPACE + "Topic",
        _ONTOLOGY_NAMESPACE + "concernsTopic",
    ),
    "status_or_stage": (
        _ONTOLOGY_NAMESPACE + "StatusStage",
        _ONTOLOGY_NAMESPACE + "hasStatusStage",
    ),
    "time_interval_or_deadline": (
        _ONTOLOGY_NAMESPACE + "RelevantTimeInterval",
        _ONTOLOGY_NAMESPACE + "hasRelevantTimeInterval",
        str(PROV.atTime),
    ),
    "organization_role": (
        _ONTOLOGY_NAMESPACE + "OrganizationRole",
        _ONTOLOGY_NAMESPACE + "assignsOrganizationRole",
        str(PROV.Role),
    ),
    "person_or_actor": (
        _ONTOLOGY_NAMESPACE + "Person",
        _ONTOLOGY_NAMESPACE + "mentions",
        str(PROV.Person),
    ),
    "communication_or_document_type": (
        _ONTOLOGY_NAMESPACE + "CommunicationDocument",
        _ONTOLOGY_NAMESPACE + "hasCommunicationDocument",
        str(PROV.Communication),
    ),
    "commercial_transaction": (
        _ONTOLOGY_NAMESPACE + "CommercialTransaction",
        _ONTOLOGY_NAMESPACE + "concernsTransaction",
    ),
    "quantity_or_measurement": (
        _ONTOLOGY_NAMESPACE + "QuantityMeasurement",
        _ONTOLOGY_NAMESPACE + "hasQuantityMeasurement",
    ),
    "requirement_issue_or_risk": (
        _ONTOLOGY_NAMESPACE + "RequirementIssueRisk",
        _ONTOLOGY_NAMESPACE + "concernsRequirementIssueRisk",
    ),
    "other_unmodeled_meaning": (),
}
_CODE_FENCE = re.compile(r"^```(?:json)?\s*|\s*```$", re.DOTALL)
_SHA256 = re.compile(r"[0-9a-f]{64}$")
_SAMPLE_DESIGNS = {
    "simple_random_without_replacement",
    "stratified_random_without_replacement",
}


def _canonical_sha256(value: object) -> str:
    """Hash a JSON-compatible artifact with a stable, whitespace-free encoding."""
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def validate_probability_sample_manifest(
    payload: object, expected_sample_size: int
) -> tuple[dict[str, object], tuple[tuple[str, str], ...]]:
    """Validate a caller-supplied probability-sample artifact without doing its math."""
    required = {
        "contract_kind",
        "contract_version",
        "population_size",
        "sample_size",
        "design_code",
        "provider_failures_retained",
        "strata",
        "selected_units",
        "selection_manifest_sha256",
    }
    if not isinstance(payload, dict) or set(payload) != required:
        raise ValueError(
            "sample manifest fields do not match the probability-sample contract"
        )
    if (
        payload["contract_kind"] != "lineageweave.semantic_coverage_probability_sample"
        or payload["contract_version"] != 3
    ):
        raise ValueError("unsupported probability-sample manifest contract")
    population_size = payload["population_size"]
    sample_size = payload["sample_size"]
    if (
        type(population_size) is not int
        or population_size < 1
        or type(sample_size) is not int
        or sample_size != expected_sample_size
        or sample_size > population_size
    ):
        raise ValueError("sample manifest population or sample size is invalid")
    if payload["design_code"] not in _SAMPLE_DESIGNS:
        raise ValueError("sample manifest must use a supported probability design")
    if payload["provider_failures_retained"] is not True:
        raise ValueError(
            "sample manifest must retain provider failures in the declared sample"
        )

    strata = payload["strata"]
    if not isinstance(strata, list) or not strata:
        raise ValueError("sample manifest requires at least one probability stratum")
    if (
        payload["design_code"] == "simple_random_without_replacement"
        and len(strata) != 1
    ) or (
        payload["design_code"] == "stratified_random_without_replacement"
        and len(strata) < 2
    ):
        raise ValueError("sample manifest strata do not match its probability design")
    stratum_fields = {
        "stratum_code",
        "population_size",
        "sample_size",
        "inclusion_probability_numerator",
        "inclusion_probability_denominator",
        "selection_frame_sha256",
    }
    stratum_codes: set[str] = set()
    stratum_populations: dict[str, int] = {}
    stratum_samples: dict[str, int] = {}
    for stratum in strata:
        if not isinstance(stratum, dict) or set(stratum) != stratum_fields:
            raise ValueError("sample manifest stratum fields are invalid")
        code = stratum["stratum_code"]
        stratum_population = stratum["population_size"]
        stratum_sample = stratum["sample_size"]
        if not isinstance(code, str) or not code.strip() or code in stratum_codes:
            raise ValueError(
                "sample manifest stratum codes must be unique and nonblank"
            )
        stratum_codes.add(code)
        if (
            type(stratum_population) is not int
            or stratum_population < 1
            or type(stratum_sample) is not int
            or stratum_sample < 1
            or stratum_sample > stratum_population
        ):
            raise ValueError("sample manifest stratum sizes are invalid")
        stratum_populations[code] = stratum_population
        stratum_samples[code] = stratum_sample
        if (
            not isinstance(stratum["selection_frame_sha256"], str)
            or _SHA256.fullmatch(stratum["selection_frame_sha256"]) is None
        ):
            raise ValueError(
                "sample manifest requires a selection-frame SHA-256 per stratum"
            )
    if sum(stratum_populations.values()) != population_size:
        raise ValueError("sample manifest stratum populations must match population_size")
    if sum(stratum_samples.values()) != sample_size:
        raise ValueError("sample manifest stratum samples must match sample_size")
    if any(
        type(stratum["inclusion_probability_numerator"]) is not int
        or type(stratum["inclusion_probability_denominator"]) is not int
        or stratum["inclusion_probability_numerator"] != stratum["sample_size"]
        or stratum["inclusion_probability_denominator"] != stratum["population_size"]
        for stratum in strata
    ):
        raise ValueError(
            "sample manifest requires the exact sample/population inclusion ratio per stratum"
        )
    selected_units = payload["selected_units"]
    selected_unit_fields = {"ordinal", "selection_token_sha256", "stratum_code"}
    if not isinstance(selected_units, list) or len(selected_units) != sample_size:
        raise ValueError("sample manifest selected-unit count must match sample_size")
    membership: list[tuple[str, str]] = []
    for ordinal, unit in enumerate(selected_units):
        if not isinstance(unit, dict) or set(unit) != selected_unit_fields:
            raise ValueError("sample manifest selected-unit fields are invalid")
        token_digest = unit["selection_token_sha256"]
        stratum_code = unit["stratum_code"]
        if unit["ordinal"] != ordinal:
            raise ValueError(
                "sample manifest selected-unit ordinals must be contiguous and ordered"
            )
        if not isinstance(token_digest, str) or _SHA256.fullmatch(token_digest) is None:
            raise ValueError("sample manifest selection-token digests must be SHA-256")
        if not isinstance(stratum_code, str) or stratum_code not in stratum_codes:
            raise ValueError("sample manifest selected unit names an unknown stratum")
        membership.append((token_digest, stratum_code))
    if len({token_digest for token_digest, _ in membership}) != sample_size:
        raise ValueError("sample manifest selection-token digests must be unique")
    if Counter(stratum_code for _, stratum_code in membership) != Counter(
        stratum_samples
    ):
        raise ValueError(
            "sample manifest selected-unit strata must match stratum sample sizes"
        )

    selection_digest = payload["selection_manifest_sha256"]
    if (
        not isinstance(selection_digest, str)
        or _SHA256.fullmatch(selection_digest) is None
        or selection_digest != _canonical_sha256(selected_units)
    ):
        raise ValueError("selected sample does not match its manifest digest")
    return (
        {
            "design_code": payload["design_code"],
            "population_size": population_size,
            "sample_size": sample_size,
            "stratum_count": len(strata),
            "selection_manifest_sha256": selection_digest,
            "corpus_inference_available": False,
        },
        tuple(membership),
    )


def validate_sampling_design_artifact(
    payload: object, sample_manifest: Mapping[str, object]
) -> dict[str, object]:
    """Replay and bind a package-owned Rust sampling-design artifact."""
    from fast_mlsirm import SamplingStratum, finite_population_proportion_design

    required = {
        "schema_version",
        "source_identity",
        "source_sha256",
        "algorithm_version",
        "population_size",
        "expected_proportion",
        "confidence_level",
        "margin_of_error",
        "critical_value",
        "uncorrected_sample_size",
        "sample_size",
        "finite_population_correction",
        "allocation_method",
        "strata",
        "stratum_sample_sizes",
        "stratum_inclusion_probability_ratios",
        "input_sha256",
        "output_sha256",
        "artifact_sha256",
    }
    if not isinstance(payload, dict) or set(payload) != required:
        raise ValueError("sampling design fields do not match the Rust artifact contract")
    strata = payload["strata"]
    if not isinstance(strata, list) or not strata:
        raise ValueError("sampling design artifact requires ordered strata")
    if any(
        not isinstance(stratum, dict)
        or set(stratum) != {"population_size", "expected_proportion"}
        for stratum in strata
    ):
        raise ValueError("sampling design artifact strata are invalid")
    try:
        replay = finite_population_proportion_design(
            payload["population_size"],
            payload["confidence_level"],
            payload["margin_of_error"],
            [
                SamplingStratum(
                    stratum["population_size"], stratum["expected_proportion"]
                )
                for stratum in strata
            ],
            allocation_method=payload["allocation_method"],
        )
    except (TypeError, ValueError) as exc:
        raise ValueError("sampling design artifact cannot be replayed by Rust") from exc
    replay_payload = json.loads(json.dumps(asdict(replay), sort_keys=True))
    if payload != replay_payload:
        raise ValueError("sampling design artifact does not match Rust replay")

    manifest_strata = sample_manifest.get("strata")
    if not isinstance(manifest_strata, list):
        raise TypeError("sample manifest strata are unavailable for design binding")
    if payload["population_size"] != sample_manifest.get("population_size") or payload[
        "sample_size"
    ] != sample_manifest.get("sample_size"):
        raise ValueError("sampling design artifact totals do not match the sample manifest")
    if [stratum["population_size"] for stratum in strata] != [
        stratum.get("population_size")
        for stratum in manifest_strata
        if isinstance(stratum, dict)
    ] or payload["stratum_sample_sizes"] != [
        stratum.get("sample_size")
        for stratum in manifest_strata
        if isinstance(stratum, dict)
    ]:
        raise ValueError("sampling design artifact allocation does not match the sample manifest")
    if payload["stratum_inclusion_probability_ratios"] != [
        [
            stratum.get("inclusion_probability_numerator"),
            stratum.get("inclusion_probability_denominator"),
        ]
        for stratum in manifest_strata
        if isinstance(stratum, dict)
    ]:
        raise ValueError(
            "sampling design artifact inclusion ratios do not match the sample manifest"
        )
    return {
        "schema_version": payload["schema_version"],
        "source_identity": payload["source_identity"],
        "source_sha256": payload["source_sha256"],
        "algorithm_version": payload["algorithm_version"],
        "input_sha256": payload["input_sha256"],
        "output_sha256": payload["output_sha256"],
        "artifact_sha256": payload["artifact_sha256"],
        "confidence_level": payload["confidence_level"],
        "margin_of_error": payload["margin_of_error"],
        "sample_size": payload["sample_size"],
        "stratum_inclusion_probability_ratios": payload[
            "stratum_inclusion_probability_ratios"
        ],
        "sampling_design_verified": True,
        "corpus_inference_available": False,
    }


def terminal_semantic_coverage_evidence(
    sample_design_artifact: Mapping[str, object],
    sample_design: Mapping[str, object],
    aggregate: Mapping[str, object],
    ontology_path: Path,
) -> dict[str, object]:
    """Build a Rust-owned terminal SRSWOR result and aggregate audit identity."""
    if sample_design.get("design_code") != "simple_random_without_replacement":
        return {
            "corpus_inference_available": False,
            "corpus_inference_unavailable_reason": (
                "stratified_terminal_estimator_not_available"
            ),
        }
    from fast_mlsirm import (
        SamplingStratum,
        finite_population_achieved_proportion,
        finite_population_proportion_design,
    )

    strata = sample_design_artifact.get("strata")
    if not isinstance(strata, list) or len(strata) != 1:
        raise ValueError("terminal SRSWOR evidence requires one design stratum")
    stratum = strata[0]
    if not isinstance(stratum, dict):
        raise ValueError("terminal SRSWOR evidence requires one design stratum")
    design = finite_population_proportion_design(
        sample_design_artifact["population_size"],
        sample_design_artifact["confidence_level"],
        sample_design_artifact["margin_of_error"],
        [SamplingStratum(stratum["population_size"], stratum["expected_proportion"])],
        allocation_method=sample_design_artifact["allocation_method"],
    )
    if design.artifact_sha256 != sample_design_artifact.get("artifact_sha256"):
        raise ValueError("terminal coverage design does not match the Rust artifact")
    sample_count = aggregate.get("sample_count")
    covered_count = aggregate.get("covered_count")
    uncovered_count = aggregate.get("uncovered_count")
    if (
        aggregate.get("complete") is not True
        or type(sample_count) is not int
        or sample_count != design.sample_size
        or type(covered_count) is not int
        or type(uncovered_count) is not int
        or covered_count + uncovered_count != sample_count
    ):
        raise ValueError("terminal coverage requires one complete design-sized audit")
    achieved = finite_population_achieved_proportion(design, covered_count)
    terminal_artifact = json.loads(json.dumps(asdict(achieved), sort_keys=True))
    ontology_sha256 = hashlib.sha256(ontology_path.read_bytes()).hexdigest()
    audit_identity = {
        "selection_manifest_sha256": sample_design["selection_manifest_sha256"],
        "ontology_sha256": ontology_sha256,
        "terminal_artifact_sha256": terminal_artifact["artifact_sha256"],
        "complete": True,
        "sample_count": sample_count,
        "covered_count": covered_count,
        "uncovered_count": uncovered_count,
        "missing_semantic_dimension_counts": aggregate.get(
            "missing_semantic_dimension_counts"
        ),
        "batch_count": aggregate.get("batch_count"),
        "minimum_trace_step_count": aggregate.get("minimum_trace_step_count"),
        "maximum_trace_step_count": aggregate.get("maximum_trace_step_count"),
    }
    audit_artifact_sha256 = _canonical_sha256(audit_identity)
    resource_iris = {
        "selection": "urn:sha256:" + str(sample_design["selection_manifest_sha256"]),
        "ontology": "urn:sha256:" + ontology_sha256,
        "terminal": "urn:sha256:" + str(terminal_artifact["artifact_sha256"]),
        "audit": "urn:sha256:" + audit_artifact_sha256,
        "activity": "urn:lineageweave:semantic-coverage-audit:" + audit_artifact_sha256,
    }
    provenance = ProvGraph()
    for name in ("selection", "ontology", "terminal", "audit"):
        provenance.add_resource(resource_iris[name], "Entity")
    provenance.add_resource(resource_iris["activity"], "Activity")
    for name in ("selection", "ontology", "terminal"):
        provenance.add_assertion(resource_iris["activity"], "used", resource_iris[name])
        provenance.add_assertion(resource_iris["audit"], "wasDerivedFrom", resource_iris[name])
    provenance.add_assertion(
        resource_iris["audit"], "wasGeneratedBy", resource_iris["activity"]
    )
    prov_o = {
        "resource_types": {
            iri: sorted(types) for iri, types in sorted(provenance.resource_types.items())
        },
        "assertions": sorted(
            (
                {
                    "subject_iri": assertion.subject_iri,
                    "relation_iri": str(PROV[assertion.relation]),
                    "object_iri": assertion.object_resource_iri,
                }
                for assertion in provenance.explicit_assertions
            ),
            key=lambda item: (
                item["subject_iri"],
                item["relation_iri"],
                item["object_iri"],
            ),
        ),
    }
    return {
        "corpus_inference_available": True,
        "rust_terminal_artifact": terminal_artifact,
        "ontology_sha256": ontology_sha256,
        "audit_artifact_sha256": audit_artifact_sha256,
        "prov_o": prov_o,
        "prov_o_sha256": _canonical_sha256(prov_o),
    }


def audit_attempt_provenance(
    *,
    selection_manifest_sha256: str,
    sampling_design_sha256: str,
    ontology_sha256: str,
    status_code: str,
    accepted_count: int,
    failed_batch_index: int | None = None,
    failure_code: str | None = None,
) -> dict[str, object]:
    """Describe an audit attempt without treating partial verdicts as a result."""
    if status_code not in {"in_progress", "completed", "rejected"}:
        raise ValueError("unsupported audit-attempt status")
    if status_code == "rejected" and not failure_code:
        raise ValueError("a rejected audit attempt requires a failure code")
    identity = {
        "selection_manifest_sha256": selection_manifest_sha256,
        "sampling_design_sha256": sampling_design_sha256,
        "ontology_sha256": ontology_sha256,
        "status_code": status_code,
        "accepted_count": accepted_count,
        "failed_batch_index": failed_batch_index,
        "failure_code": failure_code,
    }
    attempt_sha256 = _canonical_sha256(identity)
    resources = {
        "selection": "urn:sha256:" + selection_manifest_sha256,
        "design": "urn:sha256:" + sampling_design_sha256,
        "ontology": "urn:sha256:" + ontology_sha256,
        "attempt": "urn:sha256:" + attempt_sha256,
        "activity": "urn:lineageweave:semantic-coverage-attempt:" + attempt_sha256,
    }
    provenance = ProvGraph()
    for name in ("selection", "design", "ontology", "attempt"):
        provenance.add_resource(resources[name], "Entity")
    provenance.add_resource(resources["activity"], "Activity")
    for name in ("selection", "design", "ontology"):
        provenance.add_assertion(resources["activity"], "used", resources[name])
        provenance.add_assertion(resources["attempt"], "wasDerivedFrom", resources[name])
    provenance.add_assertion(
        resources["attempt"], "wasGeneratedBy", resources["activity"]
    )
    prov_o = {
        "resource_types": {
            iri: sorted(types) for iri, types in sorted(provenance.resource_types.items())
        },
        "assertions": sorted(
            (
                {
                    "subject_iri": assertion.subject_iri,
                    "relation_iri": str(PROV[assertion.relation]),
                    "object_iri": assertion.object_resource_iri,
                }
                for assertion in provenance.explicit_assertions
            ),
            key=lambda item: (
                item["subject_iri"],
                item["relation_iri"],
                item["object_iri"],
            ),
        ),
    }
    return {
        **identity,
        "attempt_sha256": attempt_sha256,
        "prov_o": prov_o,
        "prov_o_sha256": _canonical_sha256(prov_o),
    }


def _write_private_json(path: Path, payload: object) -> None:
    """Atomically replace a runtime-only JSON artifact with owner-only permissions."""
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(dir=path.parent, prefix=path.name + ".")
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            json.dump(payload, stream, sort_keys=True)
            stream.write("\n")
        os.chmod(temporary_name, 0o600)
        os.replace(temporary_name, path)
    finally:
        if os.path.exists(temporary_name):
            os.unlink(temporary_name)


def _post_json_worker(
    result_queue: Any,
    endpoint: str,
    payload: dict[str, object],
    headers: dict[str, str],
    timeout: float,
) -> None:
    """Run one provider request in a terminable child process."""
    try:
        result_queue.put((True, post_json(endpoint, payload, headers=headers, timeout=timeout)))
    except Exception as exc:
        result_queue.put((False, type(exc).__name__))


def _post_json_with_deadline(
    endpoint: str,
    payload: dict[str, object],
    *,
    headers: dict[str, str],
    timeout: float,
) -> dict[str, Any]:
    """Enforce a wall-clock deadline even when a peer keeps a socket active."""
    if timeout <= 0:
        raise ValueError("timeout must be positive")
    context = multiprocessing.get_context("spawn")
    result_queue = context.Queue(maxsize=1)
    process = context.Process(
        target=_post_json_worker,
        args=(result_queue, endpoint, payload, headers, timeout),
    )
    process.start()
    process.join(timeout)
    try:
        if process.is_alive():
            process.terminate()
            process.join()
            raise TimeoutError("semantic audit provider request exceeded its deadline")
        if result_queue.empty():
            raise RuntimeError("semantic audit provider process returned no result")
        succeeded, value = result_queue.get()
        if not succeeded:
            raise RuntimeError(f"semantic audit provider request failed: {value}")
        if not isinstance(value, dict):
            raise RuntimeError("semantic audit provider response must be an object")
        return value
    finally:
        result_queue.close()
        result_queue.join_thread()


def parse_batch_result(
    content: str,
    expected_count: int,
    supporting_terms_by_dimension: Mapping[str, tuple[str, ...]],
) -> tuple[dict[str, Any], ...]:
    """Require one ordered, governed verdict for every submitted item."""
    candidate = (
        _CODE_FENCE.sub("", content.strip())
        if content.strip().startswith("```")
        else content
    )
    try:
        payload = json.loads(candidate)
    except json.JSONDecodeError as exc:
        raise ValueError("semantic audit response must be JSON") from exc
    if not isinstance(payload, dict) or payload.get("input_count") != expected_count:
        raise ValueError(
            "semantic audit input_count does not match the submitted batch"
        )
    items = payload.get("items")
    if not isinstance(items, list) or len(items) != expected_count:
        raise ValueError("semantic audit item count does not match the submitted batch")
    expected_indexes = list(range(expected_count))
    if [
        item.get("item_index") for item in items if isinstance(item, dict)
    ] != expected_indexes:
        raise ValueError(
            "semantic audit item indexes are missing, duplicated, or unordered"
        )
    for item in items:
        if set(item) != {"item_index", "semantic_dimensions"}:
            raise ValueError("semantic audit item has an unsupported field")
        dimensions = item["semantic_dimensions"]
        if not isinstance(dimensions, list) or not dimensions or any(
            not isinstance(value, str) or value not in SEMANTIC_DIMENSIONS
            for value in dimensions
        ):
            raise ValueError("semantic audit returned an ungoverned dimension")
        if len(dimensions) != len(set(dimensions)):
            raise ValueError("semantic audit returned a duplicate semantic dimension")
    resolved = []
    for item in items:
        dimensions = item["semantic_dimensions"]
        missing = [
            dimension
            for dimension in dimensions
            if not supporting_terms_by_dimension.get(dimension)
        ]
        resolved.append(
            {
                "item_index": item["item_index"],
                "covered": not missing,
                "missing_semantic_dimensions": missing,
                "supporting_term_iris": sorted(
                    {
                        iri
                        for dimension in dimensions
                        for iri in supporting_terms_by_dimension.get(dimension, ())
                    }
                ),
            }
        )
    return tuple(resolved)


def selected_contents(
    records: Sequence[Mapping[str, Any]], selected_membership: Sequence[tuple[str, str]]
) -> list[str]:
    """Bind ordered query rows to owner-issued opaque sample-selection tokens."""
    if len(records) != len(selected_membership):
        raise ValueError(
            f"source query returned {len(records)} rows; expected exactly {len(selected_membership)}"
        )
    contents: list[str] = []
    for ordinal, record in enumerate(records):
        if tuple(record.keys()) != ("selection_token", "content_text"):
            raise ValueError(
                "source query must return exactly selection_token, content_text in manifest order"
            )
        selection_token = record["selection_token"]
        if not isinstance(selection_token, str) or not selection_token.strip():
            raise ValueError(
                "source query returned a blank or non-text selection token"
            )
        token_digest = hashlib.sha256(selection_token.encode("utf-8")).hexdigest()
        if token_digest != selected_membership[ordinal][0]:
            raise ValueError(
                "source query membership does not match the probability-sample manifest"
            )
        content = record["content_text"]
        if not isinstance(content, str) or not content.strip():
            raise ValueError("source query returned blank or non-text content")
        contents.append(content)
    return contents


def aggregate_results(
    batches: Sequence[Sequence[dict[str, Any]]], trace_counts: Sequence[int]
) -> dict[str, object]:
    """Return only non-identifying counts after every batch passed validation."""
    rows = [row for batch in batches for row in batch]
    dimensions = Counter(
        dimension for row in rows for dimension in row["missing_semantic_dimensions"]
    )
    return {
        "complete": True,
        "sample_count": len(rows),
        "covered_count": sum(row["covered"] for row in rows),
        "uncovered_count": sum(not row["covered"] for row in rows),
        "missing_semantic_dimension_counts": dict(sorted(dimensions.items())),
        "batch_count": len(batches),
        "minimum_trace_step_count": min(trace_counts),
        "maximum_trace_step_count": max(trace_counts),
    }


def _ontology_terms(path: Path) -> list[dict[str, object]]:
    """Return deterministic public semantics for every governed ontology term."""
    graph = Graph().parse(path, format="turtle")
    support_profile = path.with_name("prov-o-support-profile.ttl")
    if not support_profile.is_file():
        raise FileNotFoundError(
            "PROV-O support profile must accompany the ontology audit input: "
            f"{support_profile}"
        )
    graph.parse(support_profile, format="turtle")
    governed_kinds = {
        OWL.Class,
        OWL.ObjectProperty,
        OWL.DatatypeProperty,
        SKOS.Concept,
    }
    terms: list[dict[str, object]] = []
    for subject in sorted(
        {
            subject
            for kind in governed_kinds
            for subject in graph.subjects(RDF.type, kind)
            if isinstance(subject, URIRef)
        },
        key=str,
    ):
        terms.append(
            {
                "iri": str(subject),
                "kinds": sorted(
                    str(kind)
                    for kind in graph.objects(subject, RDF.type)
                    if kind in governed_kinds
                ),
                "labels": sorted(
                    str(value)
                    for predicate in (RDFS.label, SKOS.prefLabel)
                    for value in graph.objects(subject, predicate)
                ),
                "comments": sorted(
                    str(value) for value in graph.objects(subject, RDFS.comment)
                ),
                "domains": sorted(
                    str(value) for value in graph.objects(subject, RDFS.domain)
                ),
                "ranges": sorted(
                    str(value) for value in graph.objects(subject, RDFS.range)
                ),
                "superclasses": sorted(
                    str(value)
                    for value in graph.objects(subject, RDFS.subClassOf)
                ),
                "superproperties": sorted(
                    str(value)
                    for value in graph.objects(subject, RDFS.subPropertyOf)
                ),
                "schemes": sorted(
                    str(value) for value in graph.objects(subject, SKOS.inScheme)
                ),
            }
        )
    qualifications = {
        spec.unqualified_relation: {
            "qualification_relation": str(PROV[spec.qualification_relation]),
            "influence_class": str(PROV[spec.influence_class]),
            "influencer_relation": str(PROV[spec.influencer_relation]),
        }
        for spec in PROV_QUALIFICATIONS
    }
    terms.extend(
        {
            "iri": spec.iri,
            "kinds": [str(OWL.Class)],
            "labels": [spec.local_name],
            "comments": [],
            "domains": [],
            "ranges": [],
            "superclasses": [str(PROV[name]) for name in spec.superclasses],
            "superproperties": [],
            "schemes": [],
        }
        for spec in PROV_CLASSES.values()
    )
    terms.extend(
        {
            "iri": spec.iri,
            "kinds": [
                str(OWL.ObjectProperty)
                if spec.property_kind == "object"
                else str(OWL.DatatypeProperty)
            ],
            "labels": [spec.local_name],
            "comments": [],
            "domains": [str(PROV[name]) for name in spec.domains],
            "ranges": (
                [spec.datatype_iri]
                if spec.datatype_iri
                else [str(PROV[name]) for name in spec.ranges]
            ),
            "superclasses": [],
            "superproperties": [str(PROV[name]) for name in spec.superproperties],
            "schemes": [],
            "qualification": qualifications.get(spec.local_name),
        }
        for spec in PROV_RELATIONS.values()
    )
    return sorted(terms, key=lambda term: str(term["iri"]))


def _prompt(
    supporting_terms_by_dimension: Mapping[str, Sequence[str]],
    contents: Sequence[str],
) -> str:
    """Build a privacy-constrained exact-cardinality audit request."""
    items = [
        {"item_index": index, "source_content": content}
        for index, content in enumerate(contents)
    ]
    return (
        "Audit whether the supplied OWL/SKOS schema can represent every private item's material meaning. "
        "Never quote, paraphrase, reproduce, or expose source content or proper nouns. "
        "Treat source-specific people, organizations, places, products, projects, events, and values "
        "as instance data, not missing schema terms, when a supplied class/property can represent them. "
        "Report a missing dimension only when no supplied class/property can represent it without "
        "inventing a new schema term. "
        "Return only JSON with input_count and items. Return exactly one ordered item per item_index. "
        "Each item has exactly item_index and semantic_dimensions. Classify every material "
        "meaning into one or more supplied dimension codes; do not select ontology terms or "
        "decide coverage. Never invent a dimension name or synonym; use "
        "other_unmodeled_meaning only for material meaning outside every supplied dimension. "
        "Do not return a dimension merely because the item is a Post or text. "
        "Semantic dimensions may use only: "
        + ", ".join(sorted(SEMANTIC_DIMENSIONS))
        + ". If uncertain, use other_unmodeled_meaning.\nPUBLIC SUPPORT PROFILE:\n"
        + json.dumps(supporting_terms_by_dimension, ensure_ascii=False, sort_keys=True)
        + "\nPRIVATE INPUT (never repeat):\n"
        + json.dumps(items, ensure_ascii=False)
    )


def _response_format(expected_count: int) -> dict[str, object]:
    """Return the strict structured-output contract for one complete batch."""
    return {
        "type": "json_schema",
        "json_schema": {
            "name": "semantic_coverage_batch",
            "strict": True,
            "schema": {
                "type": "object",
                "properties": {
                    "input_count": {"const": expected_count},
                    "items": {
                        "type": "array",
                        "minItems": expected_count,
                        "maxItems": expected_count,
                        "items": {
                            "type": "object",
                            "properties": {
                                "item_index": {
                                    "type": "integer",
                                    "minimum": 0,
                                    "maximum": expected_count - 1,
                                },
                                "semantic_dimensions": {
                                    "type": "array",
                                    "minItems": 1,
                                    "uniqueItems": True,
                                    "items": {
                                        "type": "string",
                                        "enum": sorted(SEMANTIC_DIMENSIONS),
                                    },
                                },
                            },
                            "required": ["item_index", "semantic_dimensions"],
                            "additionalProperties": False,
                        },
                    },
                },
                "required": ["input_count", "items"],
                "additionalProperties": False,
            },
        },
    }


async def audit_source_content(
    *,
    source_dsn: str,
    query: str,
    sample_size: int,
    sample_manifest: object,
    sample_design_artifact: object,
    batch_size: int,
    ontology_path: Path,
    gateway_url: str,
    gateway_api_key: str,
    timeout: float,
    attempt_evidence_path: Path | None = None,
) -> dict[str, object]:
    """Run a fail-closed multi-agent audit and return aggregate evidence only."""
    if sample_size < 1 or not 1 <= batch_size <= 10:
        raise ValueError(
            "sample_size must be positive and batch_size must be between 1 and 10"
        )
    sample_design, selected_membership = validate_probability_sample_manifest(
        sample_manifest, sample_size
    )
    sample_design["rust_artifact"] = validate_sampling_design_artifact(
        sample_design_artifact, cast(Mapping[str, object], sample_manifest)
    )
    rust_artifact = cast(Mapping[str, object], sample_design["rust_artifact"])
    ontology_sha256 = hashlib.sha256(ontology_path.read_bytes()).hexdigest()
    attempt_inputs = {
        "selection_manifest_sha256": str(sample_design["selection_manifest_sha256"]),
        "sampling_design_sha256": str(rust_artifact["artifact_sha256"]),
        "ontology_sha256": ontology_sha256,
    }
    accepted_count = 0
    failed_batch_index: int | None = None

    def retain_attempt(status_code: str, failure_code: str | None = None) -> dict[str, object]:
        evidence = audit_attempt_provenance(
            **attempt_inputs,
            status_code=status_code,
            accepted_count=accepted_count,
            failed_batch_index=(
                failed_batch_index if status_code == "rejected" else None
            ),
            failure_code=failure_code,
        )
        if attempt_evidence_path is not None:
            _write_private_json(attempt_evidence_path, evidence)
        return evidence

    retain_attempt("in_progress")
    try:
        connection = await asyncpg.connect(source_dsn)
        try:
            records = await connection.fetch(query)
        finally:
            await connection.close()
        contents = selected_contents(records, selected_membership)

        terms = _ontology_terms(ontology_path)
        allowed_term_iris = {str(term["iri"]) for term in terms}
        supporting_terms_by_dimension = {
            dimension: tuple(iri for iri in expected_iris if iri in allowed_term_iris)
            for dimension, expected_iris in SEMANTIC_DIMENSION_TERM_IRIS.items()
        }
        batches: list[tuple[dict[str, Any], ...]] = []
        trace_counts: list[int] = []
        endpoint = gateway_url.rstrip("/") + "/v1/chat/completions"
        for start in range(0, len(contents), batch_size):
            failed_batch_index = start // batch_size
            window = contents[start : start + batch_size]
            response = await asyncio.to_thread(
                _post_json_with_deadline,
                endpoint,
                {
                "model": "orchestrator/auto",
                "messages": [
                    {
                        "role": "developer",
                        "content": "Preserve privacy and exact cardinality. Output JSON only.",
                    },
                    {
                        "role": "user",
                        "content": _prompt(supporting_terms_by_dimension, window),
                    },
                ],
                "orchestration_mode": "conduct",
                "include_orchestration_trace": True,
                "response_format": _response_format(len(window)),
            },
                headers={"authorization": f"Bearer {gateway_api_key}"},
                timeout=timeout,
            )
            orchestration = response.get("orchestration")
            trace = orchestration.get("trace") if isinstance(orchestration, dict) else None
            if not isinstance(trace, list) or len(trace) < 2:
                raise ValueError("semantic audit did not return multi-agent trace evidence")
            try:
                parsed_batch = parse_batch_result(
                    chat_completion_content(response),
                    len(window),
                    supporting_terms_by_dimension,
                )
            except ValueError as exc:
                raise ValueError(
                    f"semantic audit batch {start // batch_size} failed validation"
                ) from exc
            batches.append(parsed_batch)
            trace_counts.append(len(trace))
            accepted_count += len(window)
            retain_attempt("in_progress")
        failed_batch_index = None
        result = aggregate_results(batches, trace_counts)
        if result["sample_count"] != sample_size:
            raise AssertionError(
                "validated semantic audit total does not match source sample"
            )
        sample_design.update(
            terminal_semantic_coverage_evidence(
                cast(Mapping[str, object], sample_design_artifact),
                sample_design,
                result,
                ontology_path,
            )
        )
        result["sample_design"] = sample_design
        result["attempted_count"] = sample_size
        result["failed_count"] = 0
        result["attempt_provenance"] = retain_attempt("completed")
        return result
    except Exception as exc:
        retain_attempt("rejected", type(exc).__name__)
        raise


def _parser() -> argparse.ArgumentParser:
    """Build the private-content, aggregate-output CLI contract."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-dsn", required=True)
    parser.add_argument("--query-file", type=Path, required=True)
    parser.add_argument("--sample-size", type=int, required=True)
    parser.add_argument("--sample-manifest-file", type=Path, required=True)
    parser.add_argument("--sample-design-artifact-file", type=Path, required=True)
    parser.add_argument("--batch-size", type=int, default=10)
    parser.add_argument(
        "--ontology-path",
        type=Path,
        default=Path("docs/ontology/lineageweave-kg.ttl"),
    )
    parser.add_argument("--gateway-url", required=True)
    parser.add_argument(
        "--gateway-api-key-env", default="CONTEXTUAL_ORCHESTRATOR_TOKEN"
    )
    parser.add_argument("--timeout", type=float, default=300.0)
    parser.add_argument("--attempt-evidence-file", type=Path, required=True)
    return parser


def main() -> None:
    """Run the audit and print no source-derived text, even on failure."""
    args = _parser().parse_args()
    api_key = os.environ.get(args.gateway_api_key_env, "").strip()
    if not api_key:
        raise SystemExit(f"{args.gateway_api_key_env} is required")
    result = asyncio.run(
        audit_source_content(
            source_dsn=args.source_dsn,
            query=args.query_file.read_text(encoding="utf-8"),
            sample_size=args.sample_size,
            sample_manifest=json.loads(
                args.sample_manifest_file.read_text(encoding="utf-8")
            ),
            sample_design_artifact=json.loads(
                args.sample_design_artifact_file.read_text(encoding="utf-8")
            ),
            batch_size=args.batch_size,
            ontology_path=args.ontology_path,
            gateway_url=args.gateway_url,
            gateway_api_key=api_key,
            timeout=args.timeout,
            attempt_evidence_path=args.attempt_evidence_file,
        )
    )
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
