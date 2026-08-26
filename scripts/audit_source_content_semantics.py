"""Audit private source content against the ontology without emitting source text."""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
from collections import Counter
from pathlib import Path
from typing import Any, Sequence

import asyncpg

from lineageweave.http_client import chat_completion_content, post_json

SEMANTIC_DIMENSIONS = frozenset(
    {
        "event_or_activity",
        "location_or_geography",
        "product_or_service",
        "facility_asset_or_equipment",
        "topic_or_domain",
        "status_or_stage",
        "time_interval_or_deadline",
        "organization_role",
        "communication_or_document_type",
        "commercial_transaction",
        "quantity_or_measurement",
        "requirement_issue_or_risk",
        "other_unmodeled_meaning",
    }
)
_CODE_FENCE = re.compile(r"^```(?:json)?\s*|\s*```$", re.DOTALL)


def parse_batch_result(content: str, expected_count: int) -> tuple[dict[str, Any], ...]:
    """Require one ordered, governed verdict for every submitted item."""
    candidate = _CODE_FENCE.sub("", content.strip()) if content.strip().startswith("```") else content
    try:
        payload = json.loads(candidate)
    except json.JSONDecodeError as exc:
        raise ValueError("semantic audit response must be JSON") from exc
    if not isinstance(payload, dict) or payload.get("input_count") != expected_count:
        raise ValueError("semantic audit input_count does not match the submitted batch")
    items = payload.get("items")
    if not isinstance(items, list) or len(items) != expected_count:
        raise ValueError("semantic audit item count does not match the submitted batch")
    expected_indexes = list(range(expected_count))
    if [item.get("item_index") for item in items if isinstance(item, dict)] != expected_indexes:
        raise ValueError("semantic audit item indexes are missing, duplicated, or unordered")
    for item in items:
        if set(item) != {"item_index", "covered", "missing_semantic_dimensions"}:
            raise ValueError("semantic audit item has an unsupported field")
        if type(item["covered"]) is not bool:
            raise ValueError("semantic audit covered value must be boolean")
        dimensions = item["missing_semantic_dimensions"]
        if not isinstance(dimensions, list) or any(
            not isinstance(value, str) or value not in SEMANTIC_DIMENSIONS
            for value in dimensions
        ):
            raise ValueError("semantic audit returned an ungoverned dimension")
        if item["covered"] and dimensions:
            raise ValueError("a covered item cannot report a missing dimension")
    return tuple(items)


def aggregate_results(
    batches: Sequence[Sequence[dict[str, Any]]], trace_counts: Sequence[int]
) -> dict[str, object]:
    """Return only non-identifying counts after every batch passed validation."""
    rows = [row for batch in batches for row in batch]
    dimensions = Counter(
        dimension
        for row in rows
        for dimension in row["missing_semantic_dimensions"]
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


def _ontology_terms(path: Path) -> list[str]:
    """Read public class/property/concept names used as the coverage boundary."""
    return sorted(
        set(
            re.findall(
                r"^:([A-Za-z0-9_-]+)\s+a\s+"
                r"(?:owl:(?:Class|ObjectProperty|DatatypeProperty)|skos:Concept)\b",
                path.read_text(encoding="utf-8"),
                re.MULTILINE,
            )
        )
    )


def _prompt(terms: Sequence[str], contents: Sequence[str]) -> str:
    """Build a privacy-constrained exact-cardinality audit request."""
    items = [
        {"item_index": index, "source_content": content}
        for index, content in enumerate(contents)
    ]
    return (
        "Audit whether the supplied OWL/SKOS terms express every private item's material meaning. "
        "Never quote, paraphrase, reproduce, or expose source content or proper nouns. "
        "Return only JSON with input_count and items. Return exactly one ordered item per item_index. "
        "Each item has exactly item_index, covered (boolean), and missing_semantic_dimensions. "
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
    batch_size: int,
    ontology_path: Path,
    gateway_url: str,
    gateway_api_key: str,
    timeout: float,
) -> dict[str, object]:
    """Run a fail-closed multi-agent audit and return aggregate evidence only."""
    if sample_size < 1 or not 1 <= batch_size <= 10:
        raise ValueError("sample_size must be positive and batch_size must be between 1 and 10")
    connection = await asyncpg.connect(source_dsn)
    try:
        records = await connection.fetch(query)
    finally:
        await connection.close()
    if len(records) != sample_size:
        raise ValueError(f"source query returned {len(records)} rows; expected exactly {sample_size}")
    contents: list[str] = []
    for record in records:
        if tuple(record.keys()) != ("content_text",):
            raise ValueError("source query must return exactly one column aliased content_text")
        content = record["content_text"]
        if not isinstance(content, str) or not content.strip():
            raise ValueError("source query returned blank or non-text content")
        contents.append(content)

    terms = _ontology_terms(ontology_path)
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
        batches.append(parse_batch_result(chat_completion_content(response), len(window)))
        trace_counts.append(len(trace))
    result = aggregate_results(batches, trace_counts)
    if result["sample_count"] != sample_size:
        raise AssertionError("validated semantic audit total does not match source sample")
    return result


def _parser() -> argparse.ArgumentParser:
    """Build the private-content, aggregate-output CLI contract."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-dsn", required=True)
    parser.add_argument("--query-file", type=Path, required=True)
    parser.add_argument("--sample-size", type=int, required=True)
    parser.add_argument("--batch-size", type=int, default=10)
    parser.add_argument(
        "--ontology-path",
        type=Path,
        default=Path("docs/ontology/lineageweave-kg.ttl"),
    )
    parser.add_argument("--gateway-url", required=True)
    parser.add_argument("--gateway-api-key-env", default="LLM_GATEWAY_API_KEY")
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
