"""TEPP accepted-envelope evidence for LineageWeave.

TEPP main publishes ``AnalysisRunRequest`` v1 and
``AnalysisRunAccepted`` (``contract_version``, opaque ``run_id``,
``run_state=accepted``, ``idempotency_key``). It does not publish a
completed-result DTO or a production HTTP service. This module stores
that accepted acknowledgement as **aggregate transport evidence**. It
does not estimate a theta, topic, item parameter, affiliation weight,
or scientific estimand, and it never treats a LineageWeave-local
envelope as a completed TEPP measurement.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any

_ACCEPTED_CONTRACT_VERSION = 1
_ACCEPTED_RUN_STATE = "accepted"
_ACCEPTED_FIELDS = frozenset(
    {"contract_version", "run_id", "run_state", "idempotency_key"}
)
_EVIDENCE_KIND = "aggregate_transport_evidence"
_FORBIDDEN_TOKENS = (
    "theta",
    "item_parameter",
    "item_parameters",
    "item_bank",
    "topic",
    "alr",
    "topic_alr",
    "affiliation_count",
    "interval_count",
    "level_count",
    "membership_weight",
    "uncertainty",
    "time_multilevel_multi_affiliation",
)


@dataclass(frozen=True)
class TeppAcceptedEvidence:
    """Published TEPP accepted acknowledgement this product may store.

    Transport identity only. No psychometric score, membership weight,
    uncertainty, or completed-artifact identity is represented.
    """

    contract_version: int
    accepted_run_id: str
    run_state: str
    idempotency_key: str

    def evidence_sha256(self) -> str:
        """Stable digest of the published accepted fields. Never hashes a theta."""
        return tepp_accepted_evidence_sha256(
            contract_version=self.contract_version,
            accepted_run_id=self.accepted_run_id,
            run_state=self.run_state,
            idempotency_key=self.idempotency_key,
        )

    def evidence_kind(self) -> str:
        """Buyer-facing label for this stored acknowledgement."""
        return _EVIDENCE_KIND


def tepp_accepted_evidence_sha256(
    *,
    contract_version: int,
    accepted_run_id: str,
    run_state: str,
    idempotency_key: str,
) -> str:
    """Recompute the SHA-256 of a published accepted envelope.

    Encoding is length-stable canonical JSON with sorted keys. The
    digest is content-equality evidence (FIPS 180-4), not origin,
    authority, or scientific completion.
    """
    material = json.dumps(
        {
            "accepted_run_id": accepted_run_id,
            "contract_version": contract_version,
            "idempotency_key": idempotency_key,
            "run_state": run_state,
        },
        separators=(",", ":"),
        sort_keys=True,
    )
    return hashlib.sha256(material.encode()).hexdigest()


def _key_names_forbidden_measurement(token: str) -> bool:
    """True when a wire key names a completed-measurement or invented field."""
    if token in _FORBIDDEN_TOKENS or "theta" in token or "item_parameter" in token:
        return True
    if token == "topic" or token.startswith("topic_") or token.endswith("_topic"):
        return True
    if token == "alr" or token.startswith("alr_") or token.endswith("_alr"):
        return True
    if "membership" in token or "uncertainty" in token:
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


def _nonempty_text(raw: Any) -> str | None:
    """Return a stripped nonempty string, or ``None``."""
    if not isinstance(raw, str):
        return None
    text = raw.strip()
    if not text:
        return None
    return text


def parse_tepp_accepted_evidence(
    envelope: Any,
    *,
    expected_idempotency_key: str | None = None,
) -> TeppAcceptedEvidence | None:
    """Return published accepted evidence, or ``None`` when this product cannot store it.

    A LineageWeave-local ``time_multilevel_multi_affiliation`` envelope,
    a theta, IRT item parameters, a topic/ALR payload, unknown fields,
    or any run state other than ``accepted`` is not storeable evidence.
    """
    if not isinstance(envelope, dict):
        return None
    if set(envelope) != _ACCEPTED_FIELDS:
        return None
    if _walk_forbidden_tokens(envelope):
        return None
    if envelope.get("contract_version") != _ACCEPTED_CONTRACT_VERSION:
        return None
    accepted_run_id = _nonempty_text(envelope.get("run_id"))
    run_state = _nonempty_text(envelope.get("run_state"))
    idempotency_key = _nonempty_text(envelope.get("idempotency_key"))
    if accepted_run_id is None or run_state is None or idempotency_key is None:
        return None
    if run_state != _ACCEPTED_RUN_STATE:
        return None
    if (
        expected_idempotency_key is not None
        and idempotency_key != expected_idempotency_key
    ):
        return None
    return TeppAcceptedEvidence(
        contract_version=_ACCEPTED_CONTRACT_VERSION,
        accepted_run_id=accepted_run_id,
        run_state=run_state,
        idempotency_key=idempotency_key,
    )


def parse_persistable_tepp_result(envelope: Any) -> None:
    """LineageWeave-local completed envelopes are never persistable.

    TEPP has not published a versioned completed-result contract. A
    ``time_multilevel_multi_affiliation`` shape, an ``accepted`` ack,
    or a theta payload must not become a Succeeded measurement.
    """
    del envelope
    return None


def accepted_tepp_seed_envelope(*, idempotency_key: str) -> dict[str, Any]:
    """Synthetic Demo Corp accepted acknowledgement for seed and tests.

    Published accepted fields only. No organization name, source table,
    count, or theta.
    """
    return {
        "contract_version": 1,
        "run_id": "demo-tepp-accepted-opaque",
        "run_state": "accepted",
        "idempotency_key": idempotency_key,
    }


def persistable_tepp_seed_envelope() -> dict[str, Any]:
    """Synthetic LineageWeave-local envelope that must not become Succeeded.

    Kept so tests can prove the v2.12.0 shape is unsupported.
    """
    return {
        "contract_version": 1,
        "result_kind": "time_multilevel_multi_affiliation",
        "measured_at": "2026-01-12T12:45:00Z",
        "interval_count": 2,
        "level_count": 3,
        "affiliation_count": 2,
    }
