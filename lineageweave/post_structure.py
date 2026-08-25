"""Evidence-aware document structure adjudication through the orchestrator."""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from typing import Any, ClassVar, Protocol

from .http_client import post_json


@dataclass(frozen=True)
class StructureDecision:
    """One unit's adjudicated indent level, with the evidence behind it."""

    unit_index: int
    indent_level: int
    confidence: float
    evidence: str
    source_code: str = "llm"


class PostStructureClient(Protocol):
    """Port for adjudicating a post's document structure (indent levels per unit)."""

    available: bool

    def infer(
        self, post_title: str, units: list[dict[str, object]]
    ) -> tuple[StructureDecision, ...]:
        """Return one StructureDecision per unit, or raise if unavailable."""
        raise NotImplementedError


class NullPostStructureClient:
    """Fail-closed structure client used when no orchestrator is configured."""

    available = False

    def infer(
        self, post_title: str, units: list[dict[str, object]]
    ) -> tuple[StructureDecision, ...]:
        """Always raise; there is no structure-adjudication backend to call."""
        raise RuntimeError("post structure adjudication is not available")


class ContextualOrchestratorPostStructureClient:
    """Structure client backed by a real contextual-orchestrator deployment."""

    available = True

    _DECISION_ITEM_SCHEMA: ClassVar[dict[str, object]] = {
        "type": "object",
        "properties": {
            "unit_index": {"type": "integer", "minimum": 0},
            "indent_level": {"type": "integer", "minimum": 0},
            "confidence": {"type": "number", "minimum": 0, "maximum": 1},
            "evidence": {"type": "string", "minLength": 1},
        },
        "required": ["unit_index", "indent_level", "confidence", "evidence"],
        "additionalProperties": False,
    }
    _DECISION_SCHEMA: ClassVar[dict[str, object]] = {
        "type": "object",
        "properties": {
            "decisions": {
                "type": "array",
                "items": _DECISION_ITEM_SCHEMA,
            },
        },
        "required": ["decisions"],
        "additionalProperties": False,
    }

    def __init__(self, base_url: str, api_key: str, timeout: float = 600.0):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.timeout = timeout

    @classmethod
    def request_payload(
        cls, post_title: str, units: list[dict[str, object]]
    ) -> dict[str, object]:
        """Return the canonical orchestrator request for structure inference."""
        return {
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "Adjudicate the indentation level of every supplied document unit. "
                        "Return one JSON object with a decisions array, with one decision for "
                        "each unit_index. Determine indentation from ordering, numbering, "
                        "bullets, paragraph semantics, and visible explicit formatting. The "
                        "input also reports source_indent_width from leading spaces or NBSP "
                        "and declared_indent_width from HTML/CSS/OOXML. Treat declared "
                        "formatting as explicit evidence and source whitespace as supporting "
                        "evidence only. Do not mistake continuation-line alignment after a "
                        "bullet or number for a new hierarchy level. Do not invent nesting. "
                        "If evidence conflicts or is insufficient, use level 0 and low "
                        "confidence."
                    ),
                },
                {
                    "role": "user",
                    "content": json.dumps(
                        {"post_title": post_title, "ordered_units": units},
                        ensure_ascii=False,
                    ),
                },
            ],
            "response_format": {
                "type": "json_schema",
                "json_schema": {
                    "name": "post_structure_decisions",
                    "strict": True,
                    "schema": cls._DECISION_SCHEMA,
                },
            },
            "mode": "auto",
            "reasoning_effort": "auto",
            "max_tokens": 4096,
        }

    def infer(
        self, post_title: str, units: list[dict[str, object]]
    ) -> tuple[StructureDecision, ...]:
        """Ask the orchestrator to adjudicate an indent level for each unit."""
        if not units:
            return ()
        expected_indexes: set[int] = set()
        for unit in units:
            unit_index = unit.get("unit_index") if isinstance(unit, dict) else None
            if (
                type(unit_index) is not int
                or unit_index < 0
                or unit_index in expected_indexes
            ):
                raise ValueError(
                    "structure adjudication units require unique non-negative integer indexes"
                )
            expected_indexes.add(unit_index)
        response = post_json(
            f"{self.base_url}/v1/chat/completions",
            self.request_payload(post_title, units),
            headers={"authorization": f"Bearer {self.api_key}"},
            timeout=self.timeout,
        )
        parsed = json.loads(_response_content(response))
        if not isinstance(parsed, dict) or not isinstance(parsed.get("decisions"), list):
            raise ValueError(  # noqa: TRY004 - invalid provider shape is a retriable channel error.
                "structure adjudication response has no decisions array"
            )

        decisions: list[StructureDecision] = []
        for item in parsed["decisions"]:
            if not isinstance(item, dict):
                continue
            try:
                decision = StructureDecision(
                    unit_index=int(item["unit_index"]),
                    indent_level=int(item["indent_level"]),
                    confidence=float(item["confidence"]),
                    evidence=str(item["evidence"]).strip(),
                )
            except (KeyError, TypeError, ValueError):
                continue
            if (
                decision.unit_index not in expected_indexes
                or decision.indent_level < 0
                or not math.isfinite(decision.confidence)
                or not 0 <= decision.confidence <= 1
                or not decision.evidence
            ):
                continue
            decisions.append(decision)
        if not decisions:
            raise ValueError("structure adjudication produced no valid decisions")
        return tuple(sorted(decisions, key=lambda decision: decision.unit_index))


def _response_content(response: Any) -> str:
    choices = response.get("choices") if isinstance(response, dict) else None
    if not isinstance(choices, list) or not choices:
        raise ValueError("structure adjudication response has no choices")
    first_choice = choices[0]
    if not isinstance(first_choice, dict):
        raise ValueError("structure adjudication response has no choice object")
    message = first_choice.get("message")
    if not isinstance(message, dict):
        raise ValueError("structure adjudication response has no message object")
    content = message.get("content")
    if isinstance(content, str):
        return content.strip()
    if isinstance(content, list):
        text = "".join(
            part.get("text", "")
            for part in content
            if isinstance(part, dict) and isinstance(part.get("text"), str)
        )
        if text.strip():
            return text.strip()
    raise ValueError("structure adjudication response has no text content")
