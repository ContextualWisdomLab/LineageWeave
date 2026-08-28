"""Validate TEPP interval-consistency artifacts without inventing journeys."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from typing import Final

SCHEMA_VERSION: Final = "tepp.tdt_chronos_interval_consistency.v1"
MAX_ARTIFACT_BYTES: Final = 4 * 1024 * 1024
MAX_RELATIONS: Final = 100_000
ALLEN_RELATIONS: Final = (
    "before", "after", "meets", "met_by", "overlaps", "overlapped_by",
    "starts", "started_by", "during", "contains", "finishes", "finished_by", "equals",
)
_DIGEST = re.compile(r"^[0-9a-f]{64}$")


class TemporalJourneyArtifactError(ValueError):
    """A fail-closed temporal-artifact contract violation."""


@dataclass(frozen=True)
class TemporalRelation:
    """One bounded observed or closure-derived interval relation."""

    left_event_id: str
    right_event_id: str
    allen_relations: tuple[str, ...]
    observed: bool
    support_assertion_ordinals: tuple[int, ...]


@dataclass(frozen=True)
class TemporalJourneyArtifact:
    """A canonical digest-bound interval-consistency artifact."""

    run_id: str
    snapshot_id: str
    input_digest_sha256: str
    relations: tuple[TemporalRelation, ...]
    artifact_digest_sha256: str


def parse_temporal_journey_artifact(
    payload: bytes,
    *,
    expected_run_id: str,
    expected_snapshot_id: str,
    expected_input_digest_sha256: str,
    expected_artifact_digest_sha256: str,
) -> TemporalJourneyArtifact:
    """Parse canonical provider JSON and bind every caller-owned identity."""

    if not payload or len(payload) > MAX_ARTIFACT_BYTES:
        raise TemporalJourneyArtifactError("artifact size is outside the supported bound")
    if not all(
        _DIGEST.fullmatch(value)
        for value in (expected_input_digest_sha256, expected_artifact_digest_sha256)
    ):
        raise TemporalJourneyArtifactError("expected digest is not lowercase SHA-256")
    if hashlib.sha256(payload).hexdigest() != expected_artifact_digest_sha256:
        raise TemporalJourneyArtifactError("artifact bytes do not match the expected digest")
    try:
        decoded = payload.decode("utf-8")
        value = json.loads(decoded)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise TemporalJourneyArtifactError("artifact is not valid UTF-8 JSON") from exc
    if json.dumps(value, ensure_ascii=False, separators=(",", ":")) != decoded:
        raise TemporalJourneyArtifactError("artifact JSON is not canonical")
    if not isinstance(value, dict) or set(value) != {
        "schema_version", "run_id", "snapshot_id", "input_digest_sha256", "relations"
    }:
        raise TemporalJourneyArtifactError("artifact object shape is unsupported")
    if (
        value["schema_version"] != SCHEMA_VERSION
        or value["run_id"] != expected_run_id
        or value["snapshot_id"] != expected_snapshot_id
        or value["input_digest_sha256"] != expected_input_digest_sha256
    ):
        raise TemporalJourneyArtifactError("artifact identity does not match the admitted run")
    raw_relations = value["relations"]
    if not isinstance(raw_relations, list) or not 1 <= len(raw_relations) <= MAX_RELATIONS:
        raise TemporalJourneyArtifactError("relation count is outside the supported bound")
    parsed: list[TemporalRelation] = []
    previous: tuple[str, str] | None = None
    for item in raw_relations:
        if not isinstance(item, dict) or set(item) != {
            "left_event_id", "right_event_id", "allen_relations", "observed",
            "support_assertion_ordinals",
        }:
            raise TemporalJourneyArtifactError("relation object shape is unsupported")
        left, right = item["left_event_id"], item["right_event_id"]
        relations, support = item["allen_relations"], item["support_assertion_ordinals"]
        key = (left, right) if isinstance(left, str) and isinstance(right, str) else ("", "")
        if (
            not key[0].strip() or not key[1].strip() or key[0] == key[1]
            or previous is not None and previous >= key
            or not isinstance(item["observed"], bool)
            or not isinstance(relations, list) or not relations
            or any(relation not in ALLEN_RELATIONS for relation in relations)
            or relations != sorted(set(relations), key=ALLEN_RELATIONS.index)
            or len(relations) == len(ALLEN_RELATIONS)
            or not isinstance(support, list) or not support
            or any(isinstance(ordinal, bool) or not isinstance(ordinal, int) or ordinal < 0 for ordinal in support)
            or support != sorted(set(support))
        ):
            raise TemporalJourneyArtifactError("relation value is invalid or noncanonical")
        parsed.append(TemporalRelation(key[0], key[1], tuple(relations), item["observed"], tuple(support)))
        previous = key
    return TemporalJourneyArtifact(
        expected_run_id,
        expected_snapshot_id,
        expected_input_digest_sha256,
        tuple(parsed),
        expected_artifact_digest_sha256,
    )
