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
    ) -> tuple[StructureDecision, ...]: ...


class NullPostStructureClient:
    available = False

    def infer(
        self, post_title: str, units: list[dict[str, object]]
    ) -> tuple[StructureDecision, ...]:
        raise RuntimeError("post structure adjudication is not available")


class ContextualOrchestratorPostStructureClient:
    available = True

    _DECISION_SCHEMA = {
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

    def __init__(self, base_url: str, api_key: str, timeout: float = 180.0):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.timeout = timeout

    def infer(
        self, post_title: str, units: list[dict[str, object]]
    ) -> tuple[StructureDecision, ...]:
        decisions: list[StructureDecision] = []
        failures: list[Exception] = []
        for target in units:
            try:
                response = post_json(
                    f"{self.base_url}/v1/chat/completions",
                    {
                        "messages": [
                            {
                                "role": "system",
                                "content": (
                                    "You adjudicate exactly one target document unit. Return one "
                                    "JSON object only, not an array. Determine its indentation "
                                    "level from ordering, numbering, bullets, paragraph semantics, "
                                    "and visible explicit formatting in the supplied ordered units. "
                                    "Do not invent nesting. If evidence is insufficient, use level 0 "
                                    "and low confidence. The unit_index must equal target_unit_index."
                                ),
                            },
                            {
                                "role": "user",
                                "content": json.dumps(
                                    {
                                        "post_title": post_title,
                                        "target_unit_index": int(target["unit_index"]),
                                        "target_unit": target,
                                        "ordered_units": units,
                                    },
                                    ensure_ascii=False,
                                ),
                            },
                        ],
                        "response_format": {
                            "type": "json_schema",
                            "json_schema": {
                                "name": "post_structure_decision",
                                "strict": True,
                                "schema": self._DECISION_SCHEMA,
                            },
                        },
                        "mode": "auto",
                        "reasoning_effort": "auto",
                    },
                    headers={"authorization": f"Bearer {self.api_key}"},
                    timeout=self.timeout,
                )
                item = json.loads(_response_content(response))
                if not isinstance(item, dict):
                    raise ValueError("structure adjudication decision is not an object")
                decision = StructureDecision(
                    unit_index=int(item["unit_index"]),
                    indent_level=int(item["indent_level"]),
                    confidence=float(item["confidence"]),
                    evidence=str(item["evidence"]).strip(),
                )
                if decision.unit_index != int(target["unit_index"]) or decision.indent_level < 0:
                    raise ValueError("structure adjudication contains an invalid unit")
                if not math.isfinite(decision.confidence) or not 0 <= decision.confidence <= 1:
                    raise ValueError("structure adjudication confidence is out of range")
                if not decision.evidence:
                    raise ValueError("structure adjudication evidence is empty")
            except (KeyError, TypeError, ValueError, RuntimeError) as exc:
                failures.append(exc)
                continue
            decisions.append(decision)
        if not decisions and failures:
            raise ValueError("structure adjudication produced no valid decisions") from failures[-1]
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
