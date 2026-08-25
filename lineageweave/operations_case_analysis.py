"""Evidence-grounded operational case inference through contextual-orchestrator."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Protocol

from .http_client import chat_completion_content, post_json

CASE_KINDS = frozenset(
    {"claim_investigation", "rebid_handover", "external_information", "repeat_issue"}
)
FACT_TYPES = frozenset(
    {
        "order", "specification_change", "originating_order", "sales_pool",
        "discussion", "counterparty", "our_owner", "decision", "external_relation",
        "issue_pattern", "improvement_action",
    }
)


@dataclass(frozen=True)
class OperationsCaseFact:
    """One answer and the source span that supports it."""

    fact_type_code: str
    value_text: str
    evidence_text: str


@dataclass(frozen=True)
class OperationsCase:
    """One semantically classified operational case in a post."""

    case_kind_code: str
    summary_text: str
    evidence_text: str
    facts: tuple[OperationsCaseFact, ...]


class OperationsCaseAnalysisClient(Protocol):
    """Classify operational cases without keyword rules."""

    available: bool

    def analyze(self, title: str, body: str, context: str) -> tuple[OperationsCase, ...]:
        """Return every source-supported case and its facts."""
        raise NotImplementedError


class NullOperationsCaseAnalysisClient:
    """Unavailable case-analysis channel."""

    available = False

    def analyze(self, title: str, body: str, context: str) -> tuple[OperationsCase, ...]:
        """Refuse to fabricate a case when the orchestrator is unavailable."""
        raise RuntimeError("operations case analysis is unavailable")


_PROMPT = """Analyze this business record semantically. Do not use keyword matching.
Return ONLY a JSON array. Each item must have case_kind_code (one of
claim_investigation, rebid_handover, external_information, repeat_issue), summary_text,
evidence_text (a verbatim span from the body), and facts. Each fact has
fact_type_code (one of order, specification_change, originating_order,
sales_pool, discussion, counterparty, our_owner, decision, external_relation,
issue_pattern, improvement_action), value_text, and evidence_text (a verbatim body span). Return [] only when the
record supports none of the case kinds. Never fill an unsupported fact.

Stored context (hints, not proof): {context}
Title: {title}
Body: {body}
"""


def parse_operations_case_response(content: str, source_body: str) -> tuple[OperationsCase, ...] | None:
    """Validate a JSON response and require every evidence span to occur in the source."""
    try:
        payload = json.loads(content.strip())
    except json.JSONDecodeError:
        return None
    if not isinstance(payload, list):
        return None
    cases: list[OperationsCase] = []
    for item in payload:
        if not isinstance(item, dict) or item.get("case_kind_code") not in CASE_KINDS:
            return None
        summary = item.get("summary_text")
        evidence = item.get("evidence_text")
        facts = item.get("facts")
        if not isinstance(summary, str) or not summary.strip() or not isinstance(evidence, str) or evidence not in source_body or not isinstance(facts, list):
            return None
        parsed_facts: list[OperationsCaseFact] = []
        for fact in facts:
            if not isinstance(fact, dict) or fact.get("fact_type_code") not in FACT_TYPES:
                return None
            value = fact.get("value_text")
            fact_evidence = fact.get("evidence_text")
            if not isinstance(value, str) or not value.strip() or not isinstance(fact_evidence, str) or fact_evidence not in source_body:
                return None
            parsed_facts.append(OperationsCaseFact(fact["fact_type_code"], value.strip(), fact_evidence))
        cases.append(OperationsCase(item["case_kind_code"], summary.strip(), evidence, tuple(parsed_facts)))
    return tuple(cases)


class ContextualOrchestratorOperationsCaseAnalysisClient:
    """Use the provider-neutral orchestrator's multi-agent auto mode."""

    available = True

    def __init__(self, base_url: str, api_key: str, *, timeout: float = 180.0) -> None:
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._timeout = timeout

    def analyze(self, title: str, body: str, context: str) -> tuple[OperationsCase, ...]:
        """Classify cases and reject any uncited or malformed result."""
        response = post_json(
            f"{self._base_url}/v1/chat/completions",
            {"messages": [{"role": "user", "content": _PROMPT.format(context=context, title=title, body=body)}], "mode": "auto", "reasoning_effort": "auto"},
            headers={"authorization": f"Bearer {self._api_key}"},
            timeout=self._timeout,
        )
        parsed = parse_operations_case_response(chat_completion_content(response), body)
        if parsed is None:
            raise ValueError("operations case response did not match the evidence contract")
        return parsed
