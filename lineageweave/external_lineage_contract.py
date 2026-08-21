"""Versioned store-agnostic contract for external lineage consumers.

The contract accepts only bounded caller-authorized evidence references. It
contains no provider credential, database, mailbox, or network behavior. A
consumer such as Naruon can therefore submit a minimized evidence projection
without granting LineageWeave authority over the consumer's source records.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
from dataclasses import dataclass, replace
from datetime import datetime, timezone
from typing import Final, Literal, cast

CONTRACT_VERSION: Final = "1.0.0"
MAX_RECORD_COUNT: Final = 500
MAX_REFERENCE_LENGTH: Final = 160
MAX_LABEL_LENGTH: Final = 2_000
MAX_CANDIDATE_WINDOW: Final = 200
MAX_PAIR_EVALUATIONS: Final = 5_000

AnalysisScopeCode = Literal["email_lineage", "project_history", "generic_lineage"]
SourceKindCode = Literal["email", "task", "commitment", "project_event", "generic"]
CallerTruthStatusCode = Literal["observed", "authoritative_in_caller"]
ExplicitRelationCode = Literal["rfc_reply", "provider_reply", "manual_parent"]
ResultTruthStatusCode = Literal["observed", "inferred", "proposed"]
LlmStatusCode = Literal["not_requested", "unavailable", "completed"]

_ANALYSIS_SCOPES = frozenset({"email_lineage", "project_history", "generic_lineage"})
_SOURCE_KINDS = frozenset({"email", "task", "commitment", "project_event", "generic"})
_CALLER_TRUTH_STATUSES = frozenset({"observed", "authoritative_in_caller"})
_EXPLICIT_RELATIONS = frozenset({"rfc_reply", "provider_reply", "manual_parent"})
_EDGE_TRUTH_STATUSES = frozenset({"observed", "inferred"})
_LLM_STATUSES = frozenset({"not_requested", "unavailable", "completed"})
_OPAQUE_REFERENCE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:@+\-]*$")
_RESULT_DIGEST = re.compile(r"^sha256:[0-9a-f]{64}$")
_SCORE_TOLERANCE: Final = 1e-9


class LineageContractError(ValueError):
    """A fail-closed request or result contract violation.

    Attributes:
        code: Stable machine-readable reason code.
        field: Optional dotted field path associated with the violation.
    """

    def __init__(self, code: str, message: str, *, field: str | None = None) -> None:
        """Initialize one stable contract error without embedding source evidence."""

        self.code = code
        self.field = field
        suffix = f" ({field})" if field else ""
        super().__init__(f"{message}{suffix}")


@dataclass(frozen=True)
class ExplicitParent:
    """One caller-observed immediate parent relation."""

    evidence_ref: str
    relation_code: ExplicitRelationCode


@dataclass(frozen=True)
class LineageEvidenceRecord:
    """One bounded caller-owned evidence record admitted for analysis."""

    evidence_ref: str
    group_ref: str
    source_kind_code: SourceKindCode
    truth_status_code: CallerTruthStatusCode
    label: str
    occurred_at: datetime
    available_at: datetime
    secondary_key: str | None = None
    project_ref: str | None = None
    explicit_parent: ExplicitParent | None = None


@dataclass(frozen=True)
class LineageAnalysisPolicy:
    """Bounded reconstruction policy selected by the caller."""

    candidate_window: int
    maximum_pair_evaluations: int
    minimum_fused_score: float
    allow_llm: bool


@dataclass(frozen=True)
class LineageAnalysisRequest:
    """Strict versioned request for external lineage reconstruction."""

    contract_version: str
    analysis_id: str
    analysis_scope_code: AnalysisScopeCode
    knowledge_cutoff: datetime | None
    policy: LineageAnalysisPolicy
    records: tuple[LineageEvidenceRecord, ...]


@dataclass(frozen=True)
class ChannelEvidence:
    """One active reconstruction channel's exact normalized contribution."""

    channel_code: str
    score: float
    weight: float
    contribution: float


@dataclass(frozen=True)
class LineageEdgeResult:
    """One observed or inferred edge between caller-owned evidence records."""

    parent_evidence_ref: str
    child_evidence_ref: str
    relation_type_code: str
    truth_status_code: Literal["observed", "inferred"]
    fused_score: float
    channel_evidence: tuple[ChannelEvidence, ...]


@dataclass(frozen=True)
class ProjectProjection:
    """A proposed project grouping bounded to one caller group."""

    group_ref: str
    project_ref: str
    evidence_refs: tuple[str, ...]
    truth_status_code: Literal["proposed"] = "proposed"


@dataclass(frozen=True)
class LineageLimitation:
    """A machine-readable limitation disclosed with an analysis result."""

    limitation_code: str
    evidence_ref: str | None
    message: str


@dataclass(frozen=True)
class LineageAnalysisResult:
    """Deterministic external lineage result containing no caller credential."""

    contract_version: str
    analysis_id: str
    analysis_scope_code: AnalysisScopeCode
    knowledge_cutoff: datetime | None
    included_evidence_refs: tuple[str, ...]
    excluded_evidence_refs: tuple[str, ...]
    llm_status_code: LlmStatusCode
    edges: tuple[LineageEdgeResult, ...]
    project_projections: tuple[ProjectProjection, ...]
    limitations: tuple[LineageLimitation, ...]
    result_digest: str


def _raise(code: str, message: str, field: str | None = None) -> None:
    """Raise one stable contract error."""

    raise LineageContractError(code, message, field=field)


def _object(
    value: object,
    *,
    field: str,
    allowed: frozenset[str],
    required: frozenset[str],
) -> dict[str, object]:
    """Validate a strict object and reject unknown or missing fields."""

    if not isinstance(value, dict) or not all(isinstance(key, str) for key in value):
        _raise("invalid_field_type", "expected an object", field)
    typed = cast(dict[str, object], value)
    unknown = sorted(set(typed) - allowed)
    if unknown:
        _raise("unknown_field", f"unknown field {unknown[0]!r}", f"{field}.{unknown[0]}")
    missing = sorted(required - set(typed))
    if missing:
        _raise("missing_field", f"missing required field {missing[0]!r}", f"{field}.{missing[0]}")
    return typed


def _string(value: object, *, field: str, minimum: int = 1, maximum: int) -> str:
    """Return one trimmed bounded string or fail closed."""

    if not isinstance(value, str):
        _raise("invalid_field_type", "expected a string", field)
    normalized = value.strip()
    if not minimum <= len(normalized) <= maximum:
        _raise(
            "text_length_out_of_bounds",
            f"length must be {minimum}..{maximum}",
            field,
        )
    return normalized


def _opaque_reference(
    value: object,
    *,
    field: str,
    optional: bool = False,
) -> str | None:
    """Validate one bounded opaque identifier that cannot be a URL."""

    if value is None and optional:
        return None
    normalized = _string(value, field=field, maximum=MAX_REFERENCE_LENGTH)
    if "://" in normalized or not _OPAQUE_REFERENCE.fullmatch(normalized):
        _raise(
            "unsafe_opaque_reference",
            "reference must be opaque and whitespace-free",
            field,
        )
    return normalized


def _timestamp(value: object, *, field: str, optional: bool = False) -> datetime | None:
    """Parse an offset-aware RFC 3339 timestamp and normalize it to UTC."""

    if value is None and optional:
        return None
    if not isinstance(value, str):
        _raise("invalid_field_type", "expected an RFC 3339 string", field)
    candidate = value[:-1] + "+00:00" if value.endswith("Z") else value
    try:
        parsed = datetime.fromisoformat(candidate)
    except ValueError as exc:
        raise LineageContractError(
            "invalid_timestamp",
            "invalid RFC 3339 timestamp",
            field=field,
        ) from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        _raise(
            "timestamp_must_be_offset_aware",
            "timestamp must carry an offset",
            field,
        )
    return parsed.astimezone(timezone.utc)


def _enum(
    value: object,
    *,
    field: str,
    allowed: frozenset[str],
    code: str,
) -> str:
    """Validate one controlled vocabulary value."""

    if not isinstance(value, str):
        _raise("invalid_field_type", "expected a controlled string", field)
    if value not in allowed:
        _raise(code, f"unsupported value {value!r}", field)
    return value


def _integer(value: object, *, field: str, minimum: int, maximum: int) -> int:
    """Validate one integer policy value within an inclusive range."""

    if isinstance(value, bool) or not isinstance(value, int):
        _raise("invalid_field_type", "expected an integer", field)
    if not minimum <= value <= maximum:
        _raise(
            "policy_value_out_of_bounds",
            f"value must be {minimum}..{maximum}",
            field,
        )
    return value


def _number(value: object, *, field: str, minimum: float, maximum: float) -> float:
    """Validate one finite numeric policy value within an inclusive range."""

    if isinstance(value, bool) or not isinstance(value, (int, float)):
        _raise("invalid_field_type", "expected a finite number", field)
    number = float(value)
    if not math.isfinite(number) or not minimum <= number <= maximum:
        _raise(
            "policy_value_out_of_bounds",
            f"value must be {minimum}..{maximum}",
            field,
        )
    return number


def _boolean(value: object, *, field: str) -> bool:
    """Validate a real boolean without accepting integer substitutes."""

    if not isinstance(value, bool):
        _raise("invalid_field_type", "expected a boolean", field)
    return value


def _parse_explicit_parent(value: object, *, field: str) -> ExplicitParent | None:
    """Parse one optional caller-observed parent relation."""

    if value is None:
        return None
    payload = _object(
        value,
        field=field,
        allowed=frozenset({"evidence_ref", "relation_code"}),
        required=frozenset({"evidence_ref", "relation_code"}),
    )
    reference = _opaque_reference(payload["evidence_ref"], field=f"{field}.evidence_ref")
    relation = _enum(
        payload["relation_code"],
        field=f"{field}.relation_code",
        allowed=_EXPLICIT_RELATIONS,
        code="unknown_explicit_relation",
    )
    return ExplicitParent(
        cast(str, reference),
        cast(ExplicitRelationCode, relation),
    )


def _parse_record(value: object, *, index: int) -> LineageEvidenceRecord:
    """Parse one bounded evidence record from the request array."""

    field = f"records[{index}]"
    payload = _object(
        value,
        field=field,
        allowed=frozenset(
            {
                "evidence_ref",
                "group_ref",
                "source_kind_code",
                "truth_status_code",
                "label",
                "occurred_at",
                "available_at",
                "secondary_key",
                "project_ref",
                "explicit_parent",
            }
        ),
        required=frozenset(
            {
                "evidence_ref",
                "group_ref",
                "source_kind_code",
                "truth_status_code",
                "label",
                "occurred_at",
                "available_at",
            }
        ),
    )
    return LineageEvidenceRecord(
        evidence_ref=cast(
            str,
            _opaque_reference(payload["evidence_ref"], field=f"{field}.evidence_ref"),
        ),
        group_ref=cast(
            str,
            _opaque_reference(payload["group_ref"], field=f"{field}.group_ref"),
        ),
        source_kind_code=cast(
            SourceKindCode,
            _enum(
                payload["source_kind_code"],
                field=f"{field}.source_kind_code",
                allowed=_SOURCE_KINDS,
                code="unknown_source_kind",
            ),
        ),
        truth_status_code=cast(
            CallerTruthStatusCode,
            _enum(
                payload["truth_status_code"],
                field=f"{field}.truth_status_code",
                allowed=_CALLER_TRUTH_STATUSES,
                code="unknown_caller_truth_status",
            ),
        ),
        label=_string(
            payload["label"],
            field=f"{field}.label",
            maximum=MAX_LABEL_LENGTH,
        ),
        occurred_at=cast(
            datetime,
            _timestamp(payload["occurred_at"], field=f"{field}.occurred_at"),
        ),
        available_at=cast(
            datetime,
            _timestamp(payload["available_at"], field=f"{field}.available_at"),
        ),
        secondary_key=_opaque_reference(
            payload.get("secondary_key"),
            field=f"{field}.secondary_key",
            optional=True,
        ),
        project_ref=_opaque_reference(
            payload.get("project_ref"),
            field=f"{field}.project_ref",
            optional=True,
        ),
        explicit_parent=_parse_explicit_parent(
            payload.get("explicit_parent"),
            field=f"{field}.explicit_parent",
        ),
    )


def _parse_policy(value: object) -> LineageAnalysisPolicy:
    """Parse the bounded reconstruction policy."""

    payload = _object(
        value,
        field="policy",
        allowed=frozenset(
            {
                "candidate_window",
                "maximum_pair_evaluations",
                "minimum_fused_score",
                "allow_llm",
            }
        ),
        required=frozenset(
            {
                "candidate_window",
                "maximum_pair_evaluations",
                "minimum_fused_score",
                "allow_llm",
            }
        ),
    )
    return LineageAnalysisPolicy(
        candidate_window=_integer(
            payload["candidate_window"],
            field="policy.candidate_window",
            minimum=1,
            maximum=MAX_CANDIDATE_WINDOW,
        ),
        maximum_pair_evaluations=_integer(
            payload["maximum_pair_evaluations"],
            field="policy.maximum_pair_evaluations",
            minimum=1,
            maximum=MAX_PAIR_EVALUATIONS,
        ),
        minimum_fused_score=_number(
            payload["minimum_fused_score"],
            field="policy.minimum_fused_score",
            minimum=0.0,
            maximum=1.0,
        ),
        allow_llm=_boolean(payload["allow_llm"], field="policy.allow_llm"),
    )


def parse_lineage_analysis_request(payload: object) -> LineageAnalysisRequest:
    """Parse and strictly validate one external lineage analysis request."""

    data = _object(
        payload,
        field="request",
        allowed=frozenset(
            {
                "contract_version",
                "analysis_id",
                "analysis_scope_code",
                "knowledge_cutoff",
                "policy",
                "records",
            }
        ),
        required=frozenset(
            {
                "contract_version",
                "analysis_id",
                "analysis_scope_code",
                "policy",
                "records",
            }
        ),
    )
    version = _string(
        data["contract_version"],
        field="contract_version",
        maximum=16,
    )
    if version != CONTRACT_VERSION:
        _raise(
            "unsupported_contract_version",
            f"only contract version {CONTRACT_VERSION!r} is accepted",
            "contract_version",
        )
    records_payload = data["records"]
    if not isinstance(records_payload, list):
        _raise("invalid_field_type", "records must be an array", "records")
    if not 1 <= len(records_payload) <= MAX_RECORD_COUNT:
        _raise(
            "record_count_out_of_bounds",
            f"records must contain 1..{MAX_RECORD_COUNT} entries",
            "records",
        )
    records = tuple(
        _parse_record(value, index=index)
        for index, value in enumerate(records_payload)
    )
    seen: set[str] = set()
    for record in records:
        if record.evidence_ref in seen:
            _raise(
                "duplicate_evidence_ref",
                f"duplicate evidence reference {record.evidence_ref!r}",
                "records",
            )
        seen.add(record.evidence_ref)
    return LineageAnalysisRequest(
        contract_version=version,
        analysis_id=cast(
            str,
            _opaque_reference(data["analysis_id"], field="analysis_id"),
        ),
        analysis_scope_code=cast(
            AnalysisScopeCode,
            _enum(
                data["analysis_scope_code"],
                field="analysis_scope_code",
                allowed=_ANALYSIS_SCOPES,
                code="unknown_analysis_scope",
            ),
        ),
        knowledge_cutoff=_timestamp(
            data.get("knowledge_cutoff"),
            field="knowledge_cutoff",
            optional=True,
        ),
        policy=_parse_policy(data["policy"]),
        records=records,
    )


def _time_text(value: datetime | None) -> str | None:
    """Serialize an aware timestamp canonically in UTC with a ``Z`` suffix."""

    if value is None:
        return None
    if value.tzinfo is None or value.utcoffset() is None:
        _raise(
            "timestamp_must_be_offset_aware",
            "result timestamp must carry an offset",
        )
    utc = value.astimezone(timezone.utc)
    text = utc.isoformat(timespec="microseconds").replace(
        ".000000+00:00",
        "Z",
    )
    return text.replace("+00:00", "Z")


def _record_dict(record: LineageEvidenceRecord) -> dict[str, object]:
    """Serialize one evidence record without adding derived authority."""

    explicit_parent: dict[str, object] | None = None
    if record.explicit_parent is not None:
        explicit_parent = {
            "evidence_ref": record.explicit_parent.evidence_ref,
            "relation_code": record.explicit_parent.relation_code,
        }
    return {
        "evidence_ref": record.evidence_ref,
        "group_ref": record.group_ref,
        "source_kind_code": record.source_kind_code,
        "truth_status_code": record.truth_status_code,
        "label": record.label,
        "occurred_at": _time_text(record.occurred_at),
        "available_at": _time_text(record.available_at),
        "secondary_key": record.secondary_key,
        "project_ref": record.project_ref,
        "explicit_parent": explicit_parent,
    }


def serialize_lineage_analysis_request(
    request: LineageAnalysisRequest,
) -> dict[str, object]:
    """Serialize a request canonically with records ordered by evidence reference."""

    return {
        "contract_version": request.contract_version,
        "analysis_id": request.analysis_id,
        "analysis_scope_code": request.analysis_scope_code,
        "knowledge_cutoff": _time_text(request.knowledge_cutoff),
        "policy": {
            "candidate_window": request.policy.candidate_window,
            "maximum_pair_evaluations": request.policy.maximum_pair_evaluations,
            "minimum_fused_score": request.policy.minimum_fused_score,
            "allow_llm": request.policy.allow_llm,
        },
        "records": [
            _record_dict(record)
            for record in sorted(
                request.records,
                key=lambda item: item.evidence_ref,
            )
        ],
    }


def _score(value: float, *, field: str) -> float:
    """Validate and canonically round one result score in ``[0, 1]``."""

    if isinstance(value, bool) or not isinstance(value, (int, float)):
        _raise("invalid_field_type", "score must be numeric", field)
    number = float(value)
    if not math.isfinite(number) or not 0.0 <= number <= 1.0:
        _raise(
            "score_out_of_bounds",
            "score must be finite and within 0..1",
            field,
        )
    return round(number, 12)


def _validated_reference_partition(
    values: tuple[str, ...],
    *,
    field: str,
) -> frozenset[str]:
    """Validate one unique result evidence-reference partition."""

    if len(set(values)) != len(values):
        _raise(
            "duplicate_evidence_ref",
            "result partition contains duplicate references",
            field,
        )
    for value in values:
        _opaque_reference(value, field=field)
    return frozenset(values)


def _channel_dict(channel: ChannelEvidence) -> dict[str, object]:
    """Serialize one exact active-channel contribution."""

    return {
        "channel_code": _string(
            channel.channel_code,
            field="channel.channel_code",
            maximum=64,
        ),
        "score": _score(channel.score, field="channel.score"),
        "weight": _score(channel.weight, field="channel.weight"),
        "contribution": _score(
            channel.contribution,
            field="channel.contribution",
        ),
    }


def _edge_dict(
    edge: LineageEdgeResult,
    *,
    included_refs: frozenset[str],
) -> dict[str, object]:
    """Serialize one edge and verify its evidence math and references."""

    _opaque_reference(
        edge.parent_evidence_ref,
        field="edge.parent_evidence_ref",
    )
    _opaque_reference(
        edge.child_evidence_ref,
        field="edge.child_evidence_ref",
    )
    if edge.parent_evidence_ref == edge.child_evidence_ref:
        _raise("self_lineage_edge", "lineage edge cannot reference itself", "edge")
    if (
        edge.parent_evidence_ref not in included_refs
        or edge.child_evidence_ref not in included_refs
    ):
        _raise(
            "edge_reference_not_included",
            "edge references evidence outside the included partition",
            "edge",
        )
    _enum(
        edge.truth_status_code,
        field="edge.truth_status_code",
        allowed=_EDGE_TRUTH_STATUSES,
        code="unknown_result_truth_status",
    )
    fused_score = _score(edge.fused_score, field="edge.fused_score")
    channels = tuple(edge.channel_evidence)
    if not channels:
        _raise(
            "missing_channel_evidence",
            "edge must disclose at least one channel",
            "edge.channel_evidence",
        )
    channel_codes = [channel.channel_code for channel in channels]
    if len(set(channel_codes)) != len(channel_codes):
        _raise(
            "duplicate_channel_code",
            "edge contains duplicate channel codes",
            "edge.channel_evidence",
        )
    serialized_channels = [_channel_dict(channel) for channel in channels]
    weight_sum = sum(float(item["weight"]) for item in serialized_channels)
    if not math.isclose(weight_sum, 1.0, abs_tol=_SCORE_TOLERANCE):
        _raise(
            "channel_weight_sum_mismatch",
            "active channel weights must sum to one",
            "edge.channel_evidence",
        )
    for item in serialized_channels:
        expected = float(item["score"]) * float(item["weight"])
        if not math.isclose(
            float(item["contribution"]),
            expected,
            abs_tol=_SCORE_TOLERANCE,
        ):
            _raise(
                "channel_contribution_mismatch",
                "each contribution must equal score multiplied by weight",
                str(item["channel_code"]),
            )
    contribution_sum = sum(
        float(item["contribution"])
        for item in serialized_channels
    )
    if not math.isclose(
        contribution_sum,
        fused_score,
        abs_tol=_SCORE_TOLERANCE,
    ):
        _raise(
            "channel_contribution_mismatch",
            "channel contributions must reconcile to the fused score",
            "edge.channel_evidence",
        )
    return {
        "parent_evidence_ref": edge.parent_evidence_ref,
        "child_evidence_ref": edge.child_evidence_ref,
        "relation_type_code": _string(
            edge.relation_type_code,
            field="edge.relation_type_code",
            maximum=64,
        ),
        "truth_status_code": edge.truth_status_code,
        "fused_score": fused_score,
        "channel_evidence": sorted(
            serialized_channels,
            key=lambda item: cast(str, item["channel_code"]),
        ),
    }


def _project_dict(
    project: ProjectProjection,
    *,
    included_refs: frozenset[str],
) -> dict[str, object]:
    """Serialize one proposed project grouping and validate its references."""

    _opaque_reference(project.group_ref, field="project.group_ref")
    _opaque_reference(project.project_ref, field="project.project_ref")
    if project.truth_status_code != "proposed":
        _raise(
            "unknown_result_truth_status",
            "project projection must remain proposed",
            "project.truth_status_code",
        )
    evidence_refs = tuple(project.evidence_refs)
    if len(set(evidence_refs)) != len(evidence_refs):
        _raise(
            "duplicate_evidence_ref",
            "project projection contains duplicate evidence references",
            "project.evidence_refs",
        )
    for evidence_ref in evidence_refs:
        _opaque_reference(evidence_ref, field="project.evidence_refs")
        if evidence_ref not in included_refs:
            _raise(
                "project_reference_not_included",
                "project projection references evidence outside the included partition",
                evidence_ref,
            )
    return {
        "group_ref": project.group_ref,
        "project_ref": project.project_ref,
        "evidence_refs": sorted(evidence_refs),
        "truth_status_code": project.truth_status_code,
    }


def _limitation_dict(limitation: LineageLimitation) -> dict[str, object]:
    """Serialize one bounded machine-readable limitation."""

    if limitation.evidence_ref is not None:
        _opaque_reference(
            limitation.evidence_ref,
            field="limitation.evidence_ref",
        )
    return {
        "limitation_code": _string(
            limitation.limitation_code,
            field="limitation.limitation_code",
            maximum=96,
        ),
        "evidence_ref": limitation.evidence_ref,
        "message": _string(
            limitation.message,
            field="limitation.message",
            maximum=500,
        ),
    }


def serialize_lineage_analysis_result(
    result: LineageAnalysisResult,
    *,
    include_digest: bool = True,
) -> dict[str, object]:
    """Serialize a result with deterministic ordering and full invariants."""

    if result.contract_version != CONTRACT_VERSION:
        _raise(
            "unsupported_contract_version",
            "result contract version is unsupported",
            "contract_version",
        )
    _opaque_reference(result.analysis_id, field="analysis_id")
    _enum(
        result.analysis_scope_code,
        field="analysis_scope_code",
        allowed=_ANALYSIS_SCOPES,
        code="unknown_analysis_scope",
    )
    _enum(
        result.llm_status_code,
        field="llm_status_code",
        allowed=_LLM_STATUSES,
        code="unknown_llm_status",
    )
    included_refs = _validated_reference_partition(
        result.included_evidence_refs,
        field="included_evidence_refs",
    )
    excluded_refs = _validated_reference_partition(
        result.excluded_evidence_refs,
        field="excluded_evidence_refs",
    )
    if included_refs & excluded_refs:
        _raise(
            "evidence_partition_overlap",
            "included and excluded evidence partitions must be disjoint",
            "evidence_refs",
        )
    payload: dict[str, object] = {
        "contract_version": result.contract_version,
        "analysis_id": result.analysis_id,
        "analysis_scope_code": result.analysis_scope_code,
        "knowledge_cutoff": _time_text(result.knowledge_cutoff),
        "included_evidence_refs": sorted(included_refs),
        "excluded_evidence_refs": sorted(excluded_refs),
        "llm_status_code": result.llm_status_code,
        "edges": [
            _edge_dict(edge, included_refs=included_refs)
            for edge in sorted(
                result.edges,
                key=lambda item: (
                    item.child_evidence_ref,
                    item.parent_evidence_ref,
                    item.relation_type_code,
                ),
            )
        ],
        "project_projections": [
            _project_dict(project, included_refs=included_refs)
            for project in sorted(
                result.project_projections,
                key=lambda item: (item.group_ref, item.project_ref),
            )
        ],
        "limitations": [
            _limitation_dict(limitation)
            for limitation in sorted(
                result.limitations,
                key=lambda item: (
                    item.limitation_code,
                    item.evidence_ref or "",
                    item.message,
                ),
            )
        ],
    }
    if include_digest:
        if not _RESULT_DIGEST.fullmatch(result.result_digest):
            _raise(
                "invalid_result_digest",
                "result digest must be a lowercase SHA-256 identifier",
                "result_digest",
            )
        expected_digest = _digest(payload)
        if result.result_digest != expected_digest:
            _raise(
                "result_digest_mismatch",
                "result digest does not match canonical result content",
                "result_digest",
            )
        payload["result_digest"] = result.result_digest
    return payload


def _digest(payload: dict[str, object]) -> str:
    """Return a SHA-256 digest over canonical UTF-8 JSON."""

    canonical = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )
    return "sha256:" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def request_digest(request: LineageAnalysisRequest) -> str:
    """Return the deterministic digest of one semantic request."""

    return _digest(serialize_lineage_analysis_request(request))


def result_digest(result: LineageAnalysisResult) -> str:
    """Return the deterministic digest of a result excluding its digest field."""

    without_digest = replace(result, result_digest="")
    return _digest(
        serialize_lineage_analysis_result(
            without_digest,
            include_digest=False,
        )
    )
