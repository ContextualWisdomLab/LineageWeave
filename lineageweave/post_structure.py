"""Evidence-aware document structure adjudication through the orchestrator."""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from typing import Any, Protocol

from .http_client import post_json


@dataclass(frozen=True)
class StructureDecision:
    unit_index: int
    indent_level: int
    confidence: float
    evidence: str
    source_code: str = "llm"


class PostStructureClient(Protocol):
    available: bool

    def infer(
        self, post_title: str, units: list[dict[str, object]]
    ) -> tuple[StructureDecision, ...]:
        raise NotImplementedError


class NullPostStructureClient:
    available = False

    def infer(
        self, post_title: str, units: list[dict[str, object]]
    ) -> tuple[StructureDecision, ...]:
        raise RuntimeError("post structure adjudication is not available")


class ContextualOrchestratorPostStructureClient:
    available = True

    _DECISION_ITEM_SCHEMA = {
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
    _DECISION_SCHEMA = {
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

    def infer(
        self, post_title: str, units: list[dict[str, object]]
    ) -> tuple[StructureDecision, ...]:
        if not units:
            return ()
        response = post_json(
            f"{self.base_url}/v1/chat/completions",
            {
                "messages": [
                    {
                        "role": "system",
                        "content": (
                            "Adjudicate the indentation level of every supplied document unit. "
                            "Return one JSON object with a decisions array, with one decision for "
                            "each unit_index. Determine indentation from ordering, numbering, "
                            "bullets, paragraph semantics, and visible explicit formatting. Do not "
                            "invent nesting. If evidence is insufficient, use level 0 and low "
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
                        "schema": self._DECISION_SCHEMA,
                    },
                },
                "mode": "auto",
                "reasoning_effort": "auto",
                "max_tokens": 4096,
            },
            headers={"authorization": f"Bearer {self.api_key}"},
            timeout=self.timeout,
        )
        parsed = json.loads(_response_content(response))
        if not isinstance(parsed, dict) or not isinstance(parsed.get("decisions"), list):
            raise ValueError("structure adjudication response has no decisions array")

        expected_indexes = {int(unit["unit_index"]) for unit in units}
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
    message = choices[0].get("message")
    content = message.get("content") if isinstance(message, dict) else None
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
