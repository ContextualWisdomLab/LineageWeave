"""Strict, evidence-bound derived Voice classification."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Protocol

from .http_client import chat_completion_content, post_json

VOICE_CONCEPT_CODES = frozenset(
    {
        "voc",
        "vocc",
        "voco",
        "vom",
        "vop",
        "vos",
        "voe",
        "vob",
        "vor",
        "voi",
        "voso",
        "vops",
    }
)


@dataclass(frozen=True)
class DerivedVoiceAssertion:
    """One governed Voice concept supported by an exact source span."""

    voice_concept_code: str
    evidence_span_start: int
    evidence_span_end: int
    evidence_sha256: str


@dataclass(frozen=True)
class VoiceClassificationResult:
    """One successful orchestrator receipt, including valid empty results."""

    source_revision_digest: str
    orchestrator_model_receipt: str
    assertions: tuple[DerivedVoiceAssertion, ...]


class VoiceClassificationClient(Protocol):
    """Classify one authorized Post without changing its source taxonomy."""

    available: bool

    def classify(self, source_body: str) -> VoiceClassificationResult:
        """Return every source-supported governed Voice concept."""
        raise NotImplementedError


class NullVoiceClassificationClient:
    """Unavailable derived Voice channel that never fabricates a result."""

    available = False

    def classify(self, source_body: str) -> VoiceClassificationResult:
        """Refuse classification while the orchestrator is unavailable."""
        raise RuntimeError("derived Voice classification is unavailable")


class VoiceClassificationResponseContractError(ValueError):
    """A structured response failed the derived Voice evidence contract."""

    validation_code = "voice_classification_evidence_contract"
    validation_path = "$.assertions"


_PROMPT = """Classify every stakeholder or process Voice explicitly supported by this record.
Return only the strict schema. Each supported concept appears at most once and cites one
verbatim span by zero-based start-inclusive and end-exclusive character offsets. Multiple
concepts are allowed when distinct evidence supports them. Do not use keyword matching,
source category metadata, defaults, weights, or a forced winner. Return an empty assertions
array when no governed concept has direct support.

Governed concepts:
voc customer; vocc customer's customer; voco competitor; vom market; vop partner;
vos supplier; voe employee; vob internal business; vor regulator; voi investor;
voso society/community; vops process or system-generated signal.

Authorized focal Post body:
{source_body}
"""

_RESPONSE_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["assertions"],
    "properties": {
        "assertions": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": [
                    "voice_concept_code",
                    "evidence_span_start",
                    "evidence_span_end",
                    "evidence_text",
                ],
                "properties": {
                    "voice_concept_code": {
                        "type": "string",
                        "enum": sorted(VOICE_CONCEPT_CODES),
                    },
                    "evidence_span_start": {"type": "integer", "minimum": 0},
                    "evidence_span_end": {"type": "integer", "minimum": 1},
                    "evidence_text": {"type": "string", "minLength": 1},
                },
            },
        }
    },
}


def parse_voice_classification_response(
    response: object, source_body: str
) -> VoiceClassificationResult:
    """Validate receipt, closed vocabulary, and exact caller-owned spans."""
    if not isinstance(response, dict):
        raise VoiceClassificationResponseContractError(
            "orchestrator response was not an object"
        )
    receipt = response.get("id")
    if not isinstance(receipt, str) or not receipt.strip():
        raise VoiceClassificationResponseContractError(
            "orchestrator response omitted its receipt id"
        )
    try:
        payload = json.loads(chat_completion_content(response).strip())
    except (json.JSONDecodeError, TypeError, ValueError) as exc:
        raise VoiceClassificationResponseContractError(
            "Voice response was not valid structured content"
        ) from exc
    if not isinstance(payload, dict) or set(payload) != {"assertions"}:
        raise VoiceClassificationResponseContractError(
            "Voice response did not match the strict object schema"
        )
    items = payload["assertions"]
    if not isinstance(items, list):
        raise VoiceClassificationResponseContractError(
            "Voice assertions were not an array"
        )
    seen: set[str] = set()
    assertions: list[DerivedVoiceAssertion] = []
    for item in items:
        if not isinstance(item, dict) or set(item) != {
            "voice_concept_code",
            "evidence_span_start",
            "evidence_span_end",
            "evidence_text",
        }:
            raise VoiceClassificationResponseContractError(
                "Voice assertion fields were invalid"
            )
        code = item["voice_concept_code"]
        start = item["evidence_span_start"]
        end = item["evidence_span_end"]
        evidence = item["evidence_text"]
        if (
            code not in VOICE_CONCEPT_CODES
            or code in seen
            or isinstance(start, bool)
            or not isinstance(start, int)
            or isinstance(end, bool)
            or not isinstance(end, int)
            or start < 0
            or end <= start
            or end > len(source_body)
            or not isinstance(evidence, str)
            or source_body[start:end] != evidence
        ):
            raise VoiceClassificationResponseContractError(
                "Voice assertion was not bound to an exact source span"
            )
        seen.add(code)
        assertions.append(
            DerivedVoiceAssertion(
                code,
                start,
                end,
                hashlib.sha256(evidence.encode("utf-8")).hexdigest(),
            )
        )
    return VoiceClassificationResult(
        hashlib.sha256(source_body.encode("utf-8")).hexdigest(),
        receipt.strip(),
        tuple(assertions),
    )


class ContextualOrchestratorVoiceClassificationClient:
    """Use the provider-neutral orchestrator's strict multi-agent workflow."""

    available = True

    def __init__(self, base_url: str, api_key: str, *, timeout: float = 180.0) -> None:
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._timeout = timeout

    def classify(self, source_body: str) -> VoiceClassificationResult:
        """Classify the focal body and require an authoritative response receipt."""
        response = post_json(
            f"{self._base_url}/v1/chat/completions",
            {
                "model": "orchestrator/auto",
                "messages": [
                    {"role": "user", "content": _PROMPT.format(source_body=source_body)}
                ],
                "mode": "auto",
                "reasoning_effort": "auto",
                "response_format": {
                    "type": "json_schema",
                    "json_schema": {
                        "name": "derived_voice_classification",
                        "strict": True,
                        "schema": _RESPONSE_SCHEMA,
                    },
                },
            },
            headers={
                "authorization": f"Bearer {self._api_key}",
                "x-request-timeout-ms": str(round(self._timeout * 1000)),
            },
            timeout=self._timeout,
        )
        return parse_voice_classification_response(response, source_body)
