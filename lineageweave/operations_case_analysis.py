"""Evidence-grounded operational case inference through contextual-orchestrator."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from .http_client import chat_completion_content, post_json

CASE_KINDS = frozenset(
    {"claim_investigation", "rebid_handover", "external_information", "repeat_issue"}
)
FACT_TYPES = frozenset(
    {
        "order",
        "specification_change",
        "originating_order",
        "sales_pool",
        "discussion",
        "counterparty",
        "our_owner",
        "decision",
        "external_relation",
        "issue_pattern",
        "improvement_action",
    }
)
EXTERNAL_RELATION_TARGET_KINDS = frozenset(
    {"order", "project", "sales", "business_management"}
)
REQUIRED_FACT_TYPES = {
    "claim_investigation": frozenset(
        {"order", "specification_change", "originating_order", "sales_pool"}
    ),
    "rebid_handover": frozenset(
        {"discussion", "counterparty", "our_owner", "decision"}
    ),
    "external_information": frozenset({"external_relation"}),
    "repeat_issue": frozenset({"issue_pattern", "improvement_action"}),
}
MILESTONE_TYPES = frozenset(
    {
        "claim_received",
        "cause_confirmed",
        "rebid_response_requested",
        "rebid_decision_recorded",
        "handover_started",
        "handover_accepted",
    }
)
REQUIRED_MILESTONE_TYPES = {
    "claim_investigation": frozenset({"claim_received", "cause_confirmed"}),
    "rebid_handover": frozenset(
        {
            "rebid_response_requested",
            "rebid_decision_recorded",
            "handover_started",
            "handover_accepted",
        }
    ),
    "external_information": frozenset(),
    "repeat_issue": frozenset(),
}


@dataclass(frozen=True)
class OperationsCaseFact:
    """One answer and the source span that supports it."""

    fact_type_code: str
    value_text: str
    evidence_text: str
    evidence_post_id: str = ""
    evidence_input_sha256: str = ""
    relation_target_kind_code: str | None = None


@dataclass(frozen=True)
class OperationsCaseMilestone:
    """One semantically identified milestone bound to an observed source instant."""

    milestone_type_code: str
    evidence_text: str
    evidence_post_id: str
    evidence_input_sha256: str
    observed_at: datetime
    time_axis_code: str


@dataclass(frozen=True)
class OperationsCase:
    """One semantically classified operational case in a post."""

    case_kind_code: str
    summary_text: str
    evidence_text: str
    facts: tuple[OperationsCaseFact, ...]
    evidence_post_id: str = ""
    evidence_input_sha256: str = ""
    missing_fact_type_codes: tuple[str, ...] = ()
    milestones: tuple[OperationsCaseMilestone, ...] = ()
    missing_milestone_type_codes: tuple[str, ...] = ()


@dataclass(frozen=True)
class OperationsEvidenceSource:
    """One authorized source document supplied to case analysis."""

    post_id: str
    title: str
    text: str
    observed_at: datetime | None = None
    time_axis_code: str | None = None
    source_text: str | None = None

    @property
    def input_sha256(self) -> str:
        """Digest the exact evidence text submitted to the orchestrator."""
        return hashlib.sha256(self.text.encode("utf-8")).hexdigest()


def operations_analysis_input_sha256(
    sources: tuple[OperationsEvidenceSource, ...], context: str
) -> str:
    """Digest the exact ordered source window and context sent for analysis."""
    payload = {
        "context": context,
        "sources": [
            {
                "post_id": source.post_id,
                "title": source.title,
                "input_sha256": source.input_sha256,
            }
            for source in sources
        ],
    }
    encoded = json.dumps(
        payload, ensure_ascii=False, separators=(",", ":"), sort_keys=True
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


class OperationsCaseAnalysisClient(Protocol):
    """Classify operational cases without keyword rules."""

    available: bool

    def analyze(
        self, sources: tuple[OperationsEvidenceSource, ...], context: str
    ) -> tuple[OperationsCase, ...]:
        """Return every source-supported case and its facts."""
        raise NotImplementedError


class NullOperationsCaseAnalysisClient:
    """Unavailable case-analysis channel."""

    available = False

    def analyze(
        self, sources: tuple[OperationsEvidenceSource, ...], context: str
    ) -> tuple[OperationsCase, ...]:
        """Refuse to fabricate a case when the orchestrator is unavailable."""
        raise RuntimeError("operations case analysis is unavailable")


_PROMPT = """Analyze this business record semantically. Do not use keyword matching.
Return ONLY a JSON object with a cases array. Each item must have case_kind_code (one of
claim_investigation, rebid_handover, external_information, repeat_issue), summary_text,
evidence_post_id, evidence_text (a verbatim span from that numbered source), and facts. Each fact has
fact_type_code (one of order, specification_change, originating_order,
sales_pool, discussion, counterparty, our_owner, decision, external_relation,
issue_pattern, improvement_action), value_text, evidence_post_id, and evidence_text (a verbatim span from that source).
An external_relation fact must also have relation_target_kind_code (one of order,
project, sales, business_management). Other facts must use null. Classify this
semantically from the cited span; never infer it from keywords.
Each item must also have missing_fact_type_codes. Put every required fact type for that case
that is not supported anywhere in the authorized sources in this array; never invent a value or
evidence span for it. Required types are: claim_investigation = order,
specification_change, originating_order, sales_pool; rebid_handover = discussion,
counterparty, our_owner, decision; external_information = external_relation;
repeat_issue = issue_pattern, improvement_action. Return [] only when the record supports none
of the case kinds. Each item must also contain milestones and
missing_milestone_type_codes. A milestone has milestone_type_code,
evidence_post_id, and a verbatim evidence_text; its instant is assigned from
that source record and must never be generated by the model. Required milestone
types are: claim_investigation = claim_received, cause_confirmed;
rebid_handover = rebid_response_requested, rebid_decision_recorded,
handover_started, handover_accepted; the other case kinds have no milestones.
Represent every required type exactly once as cited evidence or as missing.

Stored context (hints, not proof): {context}
Authorized numbered sources:
{sources}
"""

_RESPONSE_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["cases"],
    "properties": {
        "cases": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": [
                    "case_kind_code", "summary_text", "evidence_post_id",
                    "evidence_text", "facts", "missing_fact_type_codes",
                    "milestones", "missing_milestone_type_codes",
                ],
                "properties": {
                    "case_kind_code": {"type": "string", "enum": sorted(CASE_KINDS)},
                    "summary_text": {"type": "string"},
                    "evidence_post_id": {"type": "string"},
                    "evidence_text": {"type": "string"},
                    "facts": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "additionalProperties": False,
                            "required": [
                                "fact_type_code", "value_text", "evidence_post_id",
                                "evidence_text", "relation_target_kind_code",
                            ],
                            "properties": {
                                "fact_type_code": {"type": "string", "enum": sorted(FACT_TYPES)},
                                "value_text": {"type": "string"},
                                "evidence_post_id": {"type": "string"},
                                "evidence_text": {"type": "string"},
                                "relation_target_kind_code": {
                                    "type": ["string", "null"],
                                    "enum": [None, *sorted(EXTERNAL_RELATION_TARGET_KINDS)]
                                },
                            },
                        },
                    },
                    "missing_fact_type_codes": {
                        "type": "array", "items": {"type": "string", "enum": sorted(FACT_TYPES)}
                    },
                    "milestones": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "additionalProperties": False,
                            "required": ["milestone_type_code", "evidence_post_id", "evidence_text"],
                            "properties": {
                                "milestone_type_code": {"type": "string", "enum": sorted(MILESTONE_TYPES)},
                                "evidence_post_id": {"type": "string"},
                                "evidence_text": {"type": "string"},
                            },
                        },
                    },
                    "missing_milestone_type_codes": {
                        "type": "array", "items": {"type": "string", "enum": sorted(MILESTONE_TYPES)}
                    },
                },
            },
        }
    },
}


class OperationsCaseResponseContractError(ValueError):
    """A structured response failed the bounded evidence contract."""

    validation_code = "operations_case_evidence_contract"
    validation_path = "$.cases"


def parse_operations_case_response(
    content: str, sources: tuple[OperationsEvidenceSource, ...] | str
) -> tuple[OperationsCase, ...] | None:
    """Require every evidence span and post id to match an authorized source."""
    legacy_focal = isinstance(sources, str)
    if legacy_focal:
        sources = (OperationsEvidenceSource("focal", "focal", sources),)
    sources_by_id = {source.post_id: source for source in sources}
    try:
        payload = json.loads(content.strip())
    except json.JSONDecodeError:
        return None
    if isinstance(payload, dict) and set(payload) == {"cases"}:
        payload = payload["cases"]
    if not isinstance(payload, list):
        return None
    cases: list[OperationsCase] = []
    seen_case_kinds: set[str] = set()
    for item in payload:
        if not isinstance(item, dict) or item.get("case_kind_code") not in CASE_KINDS:
            return None
        if item["case_kind_code"] in seen_case_kinds:
            return None
        seen_case_kinds.add(item["case_kind_code"])
        summary = item.get("summary_text")
        evidence = item.get("evidence_text")
        evidence_post_id = item.get("evidence_post_id") or (
            "focal" if legacy_focal else None
        )
        facts = item.get("facts")
        missing_fact_types = item.get("missing_fact_type_codes")
        milestones = item.get("milestones")
        missing_milestone_types = item.get("missing_milestone_type_codes")
        evidence_source = sources_by_id.get(evidence_post_id)
        if (
            not isinstance(summary, str)
            or not summary.strip()
            or not isinstance(evidence, str)
            or not evidence.strip()
            or evidence_source is None
            or evidence not in evidence_source.text
            or not isinstance(facts, list)
            or not isinstance(missing_fact_types, list)
            or not isinstance(milestones, list)
            or not isinstance(missing_milestone_types, list)
        ):
            return None
        parsed_facts: list[OperationsCaseFact] = []
        for fact in facts:
            if (
                not isinstance(fact, dict)
                or fact.get("fact_type_code") not in FACT_TYPES
            ):
                return None
            value = fact.get("value_text")
            fact_evidence = fact.get("evidence_text")
            fact_post_id = fact.get("evidence_post_id") or (
                "focal" if legacy_focal else None
            )
            fact_source = sources_by_id.get(fact_post_id)
            relation_target_kind = fact.get("relation_target_kind_code")
            if (
                not isinstance(value, str)
                or not value.strip()
                or not isinstance(fact_evidence, str)
                or not fact_evidence.strip()
                or fact_source is None
                or fact_evidence not in fact_source.text
                or (
                    fact["fact_type_code"] == "external_relation"
                    and relation_target_kind not in EXTERNAL_RELATION_TARGET_KINDS
                )
                or (
                    fact["fact_type_code"] != "external_relation"
                    and relation_target_kind is not None
                )
            ):
                return None
            parsed_facts.append(
                OperationsCaseFact(
                    fact["fact_type_code"],
                    value.strip(),
                    fact_evidence,
                    fact_source.post_id,
                    fact_source.input_sha256,
                    relation_target_kind,
                )
            )
        supported_type_counts = {
            fact_type: sum(
                fact.fact_type_code == fact_type for fact in parsed_facts
            )
            for fact_type in FACT_TYPES
        }
        supported_types = {
            fact_type for fact_type, count in supported_type_counts.items() if count
        }
        if any(
            not isinstance(code, str) or code not in FACT_TYPES
            for code in missing_fact_types
        ):
            return None
        missing_types = set(missing_fact_types)
        required_types = REQUIRED_FACT_TYPES[item["case_kind_code"]]
        if (
            any(supported_type_counts[fact_type] > 1 for fact_type in required_types)
            or len(missing_types) != len(missing_fact_types)
            or not missing_types.issubset(required_types)
            or supported_types.intersection(missing_types)
            or not required_types.issubset(supported_types.union(missing_types))
        ):
            return None
        parsed_milestones: list[OperationsCaseMilestone] = []
        for milestone in milestones:
            if (
                not isinstance(milestone, dict)
                or milestone.get("milestone_type_code") not in MILESTONE_TYPES
            ):
                return None
            milestone_evidence = milestone.get("evidence_text")
            milestone_post_id = milestone.get("evidence_post_id") or (
                "focal" if legacy_focal else None
            )
            milestone_source = sources_by_id.get(milestone_post_id)
            if (
                not isinstance(milestone_evidence, str)
                or not milestone_evidence.strip()
                or milestone_source is None
                or milestone_evidence not in milestone_source.text
                or milestone_source.observed_at is None
                or milestone_source.time_axis_code
                not in {"event_occurred_at", "created_at"}
            ):
                return None
            parsed_milestones.append(
                OperationsCaseMilestone(
                    milestone["milestone_type_code"],
                    milestone_evidence,
                    milestone_source.post_id,
                    milestone_source.input_sha256,
                    milestone_source.observed_at,
                    milestone_source.time_axis_code,
                )
            )
        supported_milestone_types = {
            value.milestone_type_code for value in parsed_milestones
        }
        required_milestones = REQUIRED_MILESTONE_TYPES[item["case_kind_code"]]
        if (
            len(supported_milestone_types) != len(parsed_milestones)
            or any(
                not isinstance(code, str) or code not in MILESTONE_TYPES
                for code in missing_milestone_types
            )
            or len(set(missing_milestone_types)) != len(missing_milestone_types)
            or supported_milestone_types.intersection(missing_milestone_types)
            or supported_milestone_types.union(missing_milestone_types)
            != required_milestones
        ):
            return None
        milestone_by_type = {
            value.milestone_type_code: value for value in parsed_milestones
        }
        for start_code, end_code in (
            ("claim_received", "cause_confirmed"),
            ("rebid_response_requested", "rebid_decision_recorded"),
            ("handover_started", "handover_accepted"),
        ):
            if (
                start_code in milestone_by_type
                and end_code in milestone_by_type
                and milestone_by_type[end_code].observed_at
                < milestone_by_type[start_code].observed_at
            ):
                return None
        cases.append(
            OperationsCase(
                item["case_kind_code"],
                summary.strip(),
                evidence,
                tuple(parsed_facts),
                evidence_source.post_id,
                evidence_source.input_sha256,
                tuple(missing_fact_types),
                tuple(parsed_milestones),
                tuple(missing_milestone_types),
            )
        )
    return tuple(cases)


class ContextualOrchestratorOperationsCaseAnalysisClient:
    """Use the provider-neutral orchestrator's multi-agent auto mode."""

    available = True

    def __init__(self, base_url: str, api_key: str, *, timeout: float = 180.0) -> None:
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._timeout = timeout

    def analyze(
        self, sources: tuple[OperationsEvidenceSource, ...], context: str
    ) -> tuple[OperationsCase, ...]:
        """Classify cases and reject any uncited or malformed result."""
        response = post_json(
            f"{self._base_url}/v1/chat/completions",
            {
                "model": "orchestrator/auto",
                "messages": [
                    {
                        "role": "user",
                        "content": _PROMPT.format(
                            context=context,
                            sources="\n\n".join(
                                f"[Source {index}] post_id={source.post_id}\nTitle: {source.title}\n{source.text}"
                                for index, source in enumerate(sources, 1)
                            ),
                        ),
                    }
                ],
                "mode": "auto",
                "reasoning_effort": "auto",
                "response_format": {
                    "type": "json_schema",
                    "json_schema": {
                        "name": "operations_case_analysis",
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
        parsed = parse_operations_case_response(
            chat_completion_content(response), sources
        )
        if parsed is None:
            raise OperationsCaseResponseContractError(
                "operations case response did not match the evidence contract"
            )
        return parsed
