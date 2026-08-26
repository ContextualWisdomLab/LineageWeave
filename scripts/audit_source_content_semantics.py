"""Audit private source content against the ontology without emitting source text."""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import os
import re
from collections import Counter
from collections.abc import Mapping, Sequence
from decimal import Decimal
from pathlib import Path
from typing import Any

import asyncpg
from rdflib import Graph, URIRef
from rdflib.namespace import OWL, RDF, RDFS, SKOS

from lineageweave.http_client import chat_completion_content, post_json
from lineageweave.prov_o import PROV, PROV_CLASSES, PROV_QUALIFICATIONS, PROV_RELATIONS

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
_CODE_FENCE = re.compile(r"^```(?:json)?\s*|\s*```$", re.DOTALL)
_INCLUSION_PROBABILITY = re.compile(r"(?:0\.(?:0*[1-9]\d*)|1(?:\.0+)?)$")
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
        or payload["contract_version"] != 2
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
        "inclusion_probability",
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
            not isinstance(stratum["inclusion_probability"], str)
            or _INCLUSION_PROBABILITY.fullmatch(stratum["inclusion_probability"])
            is None
        ):
            raise ValueError(
                "sample manifest requires a known inclusion probability per stratum"
            )
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
    for stratum in strata:
        declared_probability = Decimal(stratum["inclusion_probability"])
        actual_probability = Decimal(stratum["sample_size"]) / Decimal(
            stratum["population_size"]
        )
        if abs(declared_probability - actual_probability) > Decimal("1e-12"):
            raise ValueError(
                "sample manifest inclusion probability must match the stratum sampling fraction"
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


def parse_batch_result(
    content: str, expected_count: int, allowed_term_iris: frozenset[str]
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
        if set(item) != {
            "item_index",
            "covered",
            "missing_semantic_dimensions",
            "supporting_term_iris",
        }:
            raise ValueError("semantic audit item has an unsupported field")
        if type(item["covered"]) is not bool:
            raise ValueError("semantic audit covered value must be boolean")
        dimensions = item["missing_semantic_dimensions"]
        if not isinstance(dimensions, list) or any(
            not isinstance(value, str) or value not in SEMANTIC_DIMENSIONS
            for value in dimensions
        ):
            raise ValueError("semantic audit returned an ungoverned dimension")
        if len(dimensions) != len(set(dimensions)):
            raise ValueError("semantic audit returned a duplicate missing dimension")
        supporting_terms = item["supporting_term_iris"]
        if not isinstance(supporting_terms, list) or any(
            not isinstance(value, str) or value not in allowed_term_iris
            for value in supporting_terms
        ):
            raise ValueError("semantic audit returned an ungoverned supporting term")
        if len(supporting_terms) != len(set(supporting_terms)):
            raise ValueError("semantic audit returned a duplicate supporting term")
        if item["covered"] and dimensions:
            raise ValueError("a covered item cannot report a missing dimension")
        if item["covered"] and not supporting_terms:
            raise ValueError("a covered item requires a supporting ontology term")
        if not item["covered"] and not dimensions:
            raise ValueError("an uncovered item requires a missing dimension")
    return tuple(items)


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
    if support_profile.is_file():
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


def _prompt(terms: Sequence[Mapping[str, object]], contents: Sequence[str]) -> str:
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
        "Each item has exactly item_index, covered (boolean), missing_semantic_dimensions, "
        "and supporting_term_iris. Use only supplied ontology IRIs. A covered item requires "
        "one or more supporting IRIs and no missing dimensions. An uncovered item requires "
        "one or more missing dimensions; do not duplicate values. Never invent a dimension "
        "name or synonym; use other_unmodeled_meaning for meaning outside the enum. "
        "Do not treat Post or an opaque text literal as semantic coverage. Missing dimensions may use only: "
        + ", ".join(sorted(SEMANTIC_DIMENSIONS))
        + ". If uncertain, use other_unmodeled_meaning.\nONTOLOGY TERMS:\n"
        + json.dumps(list(terms), ensure_ascii=False)
        + "\nPRIVATE INPUT (never repeat):\n"
        + json.dumps(items, ensure_ascii=False)
    )


async def audit_source_content(
    *,
    source_dsn: str,
    query: str,
    sample_size: int,
    sample_manifest: object,
    batch_size: int,
    ontology_path: Path,
    gateway_url: str,
    gateway_api_key: str,
    timeout: float,
) -> dict[str, object]:
    """Run a fail-closed multi-agent audit and return aggregate evidence only."""
    if sample_size < 1 or not 1 <= batch_size <= 10:
        raise ValueError(
            "sample_size must be positive and batch_size must be between 1 and 10"
        )
    sample_design, selected_membership = validate_probability_sample_manifest(
        sample_manifest, sample_size
    )
    connection = await asyncpg.connect(source_dsn)
    try:
        records = await connection.fetch(query)
    finally:
        await connection.close()
    contents = selected_contents(records, selected_membership)

    terms = _ontology_terms(ontology_path)
    allowed_term_iris = frozenset(str(term["iri"]) for term in terms)
    batches: list[tuple[dict[str, Any], ...]] = []
    trace_counts: list[int] = []
    endpoint = gateway_url.rstrip("/") + "/v1/chat/completions"
    for start in range(0, len(contents), batch_size):
        window = contents[start : start + batch_size]
        response = await asyncio.to_thread(
            post_json,
            endpoint,
            {
                "model": "contextual-orchestrator",
                "messages": [
                    {
                        "role": "developer",
                        "content": "Preserve privacy and exact cardinality. Output JSON only.",
                    },
                    {"role": "user", "content": _prompt(terms, window)},
                ],
                "orchestration_mode": "conduct",
                "include_orchestration_trace": True,
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
                chat_completion_content(response), len(window), allowed_term_iris
            )
        except ValueError as exc:
            raise ValueError(
                f"semantic audit batch {start // batch_size} failed validation"
            ) from exc
        batches.append(parsed_batch)
        trace_counts.append(len(trace))
    result = aggregate_results(batches, trace_counts)
    if result["sample_count"] != sample_size:
        raise AssertionError(
            "validated semantic audit total does not match source sample"
        )
    result["sample_design"] = sample_design
    result["attempted_count"] = sample_size
    result["failed_count"] = 0
    return result


def _parser() -> argparse.ArgumentParser:
    """Build the private-content, aggregate-output CLI contract."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-dsn", required=True)
    parser.add_argument("--query-file", type=Path, required=True)
    parser.add_argument("--sample-size", type=int, required=True)
    parser.add_argument("--sample-manifest-file", type=Path, required=True)
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
            batch_size=args.batch_size,
            ontology_path=args.ontology_path,
            gateway_url=args.gateway_url,
            gateway_api_key=api_key,
            timeout=args.timeout,
        )
    )
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
