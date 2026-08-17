"""Persistable TEPP measurement envelope for LineageWeave.

TEPP is consumed through :class:`lineageweave.tepp_client.TeppClient`
only. This module does not estimate a theta, IRT item parameter, topic,
or ALR. It accepts a **time / multilevel / multi-affiliation** result
that a live transport already produced, or returns ``None`` so the run
stays Failed / ``tepp_result_not_persisted``.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

_PERSISTABLE_KIND = "time_multilevel_multi_affiliation"
_FORBIDDEN_TOKENS = (
    "theta",
    "item_parameter",
    "item_parameters",
    "item_bank",
    "topic",
    "alr",
    "topic_alr",
)


@dataclass(frozen=True)
class TeppPersistableResult:
    """Aggregates a persistable TEPP result may store on an analysis run.

    Counts and clocks only. No psychometric score, item bank, or topic
    label is represented.
    """

    contract_version: int
    result_kind: str
    measured_at: datetime
    interval_count: int
    level_count: int
    affiliation_count: int

    def result_sha256(self) -> str:
        """Stable digest of the persistable aggregates. Never hashes a theta."""
        material = json.dumps(
            {
                "affiliation_count": self.affiliation_count,
                "contract_version": self.contract_version,
                "interval_count": self.interval_count,
                "level_count": self.level_count,
                "measured_at": _utc_iso(self.measured_at),
                "result_kind": self.result_kind,
            },
            separators=(",", ":"),
            sort_keys=True,
        )
        return hashlib.sha256(material.encode()).hexdigest()


def _utc_iso(value: datetime) -> str:
    """Normalize a clock to UTC ISO-8601 with a ``Z`` suffix."""
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _key_names_forbidden_measurement(token: str) -> bool:
    """True when a wire key names a theta, IRT item, topic, or ALR field."""
    if token in _FORBIDDEN_TOKENS or "theta" in token or "item_parameter" in token:
        return True
    if token == "topic" or token.startswith("topic_") or token.endswith("_topic"):
        return True
    if token == "alr" or token.startswith("alr_") or token.endswith("_alr"):
        return True
    return False


def _walk_forbidden_tokens(value: Any) -> bool:
    """True when any object key names a forbidden measurement field."""
    if isinstance(value, dict):
        for key, nested in value.items():
            token = str(key).casefold().replace("-", "_")
            if _key_names_forbidden_measurement(token):
                return True
            if _walk_forbidden_tokens(nested):
                return True
        return False
    if isinstance(value, list):
        return any(_walk_forbidden_tokens(item) for item in value)
    return False


def _parse_measured_at(raw: Any) -> datetime | None:
    """Parse an ISO-8601 clock. Naive values are treated as UTC."""
    if not isinstance(raw, str) or not raw.strip():
        return None
    text = raw.strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _non_negative_int(raw: Any) -> int | None:
    """Return a non-negative int, or ``None`` when the value is not one."""
    if isinstance(raw, bool) or not isinstance(raw, int):
        return None
    if raw < 0:
        return None
    return raw


def parse_persistable_tepp_result(envelope: Any) -> TeppPersistableResult | None:
    """Return a persistable TEPP result, or ``None`` when this product cannot store it.

    An ``accepted`` ack, a theta, IRT item parameters, a topic/ALR
    payload, or a missing time / multilevel / multi-affiliation field
    is not persistable.
    """
    if not isinstance(envelope, dict):
        return None
    if _walk_forbidden_tokens(envelope):
        return None
    if envelope.get("contract_version") != 1:
        return None
    if envelope.get("result_kind") != _PERSISTABLE_KIND:
        return None
    measured_at = _parse_measured_at(envelope.get("measured_at"))
    interval_count = _non_negative_int(envelope.get("interval_count"))
    level_count = _non_negative_int(envelope.get("level_count"))
    affiliation_count = _non_negative_int(envelope.get("affiliation_count"))
    if (
        measured_at is None
        or interval_count is None
        or level_count is None
        or affiliation_count is None
    ):
        return None
    return TeppPersistableResult(
        contract_version=1,
        result_kind=_PERSISTABLE_KIND,
        measured_at=measured_at,
        interval_count=interval_count,
        level_count=level_count,
        affiliation_count=affiliation_count,
    )


def persistable_tepp_seed_envelope() -> dict[str, Any]:
    """Synthetic Demo Corp persistable envelope for seed and in-process tests.

    Aggregates only. No organization name, source table, or theta.
    """
    return {
        "contract_version": 1,
        "result_kind": _PERSISTABLE_KIND,
        "measured_at": "2026-01-12T12:45:00Z",
        "interval_count": 2,
        "level_count": 3,
        "affiliation_count": 2,
    }
