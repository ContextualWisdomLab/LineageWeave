"""Versioned, store-agnostic provider contract for bounded lineage analysis.

The contract accepts evidence that a caller has already authorized. It never
opens a database, accepts provider credentials, or returns a source identifier
that was not present in the request.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from hashlib import sha256

from .adjudication_client import AdjudicationClient
from .models import Record
from .reconstruct import reconstruct

CONTRACT_VERSION = "lineage-analysis/v1"
_MAX_REFERENCE_LENGTH = 200
_MAX_TEXT_LENGTH = 8_000


def _required_text(value: str, field_name: str, *, maximum: int = _MAX_REFERENCE_LENGTH) -> str:
    """Validate and return a bounded non-empty contract string."""
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must be a non-empty string")
    if len(value) > maximum:
        raise ValueError(f"{field_name} exceeds the {maximum}-character limit")
    return value


def _utc_timestamp(value: datetime, field_name: str) -> datetime:
    """Require an explicitly timezone-aware timestamp and normalize it to UTC."""
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{field_name} must be timezone-aware")
    return value.astimezone(UTC)


def _timestamp_json(value: datetime) -> str:
    """Serialize a timestamp in one canonical UTC representation."""
    return _utc_timestamp(value, "timestamp").isoformat().replace("+00:00", "Z")


@dataclass(frozen=True)
class EmailEvidence:
    """Email evidence kept separate from semantic/project lineage signals."""

    rfc_message_id: str | None = None
    references: tuple[str, ...] = ()
    in_reply_to: str | None = None
    provider_thread_id: str | None = None
    raw_content_hash: str | None = None
    participant_refs: tuple[str, ...] = ()
    attachment_refs: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, object]:
        """Return the RFC/provider evidence without flattening it into a score."""
        return {
            "rfc_message_id": self.rfc_message_id,
            "references": list(self.references),
            "in_reply_to": self.in_reply_to,
            "provider_thread_id": self.provider_thread_id,
            "raw_content_hash": self.raw_content_hash,
            "participant_refs": list(self.participant_refs),
            "attachment_refs": list(self.attachment_refs),
        }


@dataclass(frozen=True)
class LineageProjectHint:
    """Caller-supplied project hint; it is never an authoritative project state."""

    evidence_ref: str
    project_ref: str
    label: str

    def validate(self, evidence_refs: set[str]) -> None:
        """Ensure the hint only points at evidence in this request."""
        _required_text(self.evidence_ref, "project_hint.evidence_ref")
        _required_text(self.project_ref, "project_hint.project_ref")
        _required_text(self.label, "project_hint.label", maximum=_MAX_TEXT_LENGTH)
        if self.evidence_ref not in evidence_refs:
            raise ValueError("project hint references evidence outside the request")

    def to_dict(self) -> dict[str, str]:
        """Return the bounded project hint representation."""
        return {
            "evidence_ref": self.evidence_ref,
            "project_ref": self.project_ref,
            "label": self.label,
        }


@dataclass(frozen=True)
class LineageEvidenceRecord:
    """One already-authorized record submitted under an opaque caller reference."""

    evidence_ref: str
    group_key: str
    label: str
    occurred_at: datetime
    available_at: datetime
    secondary_key: str = ""
    body_text: str = ""
    email: EmailEvidence | None = None

    def validate(self, *, max_body_chars: int) -> None:
        """Validate identity, content bounds, and both independent clocks."""
        _required_text(self.evidence_ref, "evidence.evidence_ref")
        _required_text(self.group_key, "evidence.group_key")
        _required_text(self.label, "evidence.label", maximum=_MAX_TEXT_LENGTH)
        if not isinstance(self.body_text, str) or len(self.body_text) > max_body_chars:
            raise ValueError(f"evidence.body_text exceeds the {max_body_chars}-character limit")
        if self.secondary_key and len(self.secondary_key) > _MAX_REFERENCE_LENGTH:
            raise ValueError("evidence.secondary_key exceeds the reference limit")
        _utc_timestamp(self.occurred_at, "evidence.occurred_at")
        _utc_timestamp(self.available_at, "evidence.available_at")
        if self.email is not None:
            for field_name in (
                "rfc_message_id",
                "in_reply_to",
                "provider_thread_id",
                "raw_content_hash",
            ):
                value = getattr(self.email, field_name)
                if value is not None:
                    _required_text(value, f"evidence.email.{field_name}", maximum=_MAX_TEXT_LENGTH)
            for field_name in ("references", "participant_refs", "attachment_refs"):
                for value in getattr(self.email, field_name):
                    _required_text(value, f"evidence.email.{field_name}")

    def to_dict(self) -> dict[str, object]:
        """Return the source-shaped record used for canonical request hashing."""
        return {
            "evidence_ref": self.evidence_ref,
            "group_key": self.group_key,
            "label": self.label,
            "occurred_at": _timestamp_json(self.occurred_at),
            "available_at": _timestamp_json(self.available_at),
            "secondary_key": self.secondary_key,
            "body_text": self.body_text,
            "email": self.email.to_dict() if self.email is not None else None,
        }


@dataclass(frozen=True)
class LineageAnalysisPolicy:
    """Bounded, caller-visible policy for one stateless provider invocation."""

    max_evidence_records: int = 500
    max_body_chars: int = 4_000

    def validate(self) -> None:
        """Reject unbounded or nonsensical request budgets."""
        if not 1 <= self.max_evidence_records <= 5_000:
            raise ValueError("max_evidence_records must be between 1 and 5000")
        if not 0 <= self.max_body_chars <= _MAX_TEXT_LENGTH:
            raise ValueError(f"max_body_chars must be between 0 and {_MAX_TEXT_LENGTH}")

    def to_dict(self) -> dict[str, int]:
        """Return the policy values included in request identity."""
        return {
            "max_evidence_records": self.max_evidence_records,
            "max_body_chars": self.max_body_chars,
        }


@dataclass(frozen=True)
class LineageAnalysisRequest:
    """Immutable request that binds authorization, evidence, policy, and cutoff."""

    analysis_id: str
    authorization_scope_ref: str
    knowledge_cutoff: datetime
    evidence: tuple[LineageEvidenceRecord, ...]
    project_hints: tuple[LineageProjectHint, ...] = ()
    policy: LineageAnalysisPolicy = LineageAnalysisPolicy()

    def validate(self) -> None:
        """Validate the complete request before any reconstruction occurs."""
        _required_text(self.analysis_id, "analysis_id")
        _required_text(self.authorization_scope_ref, "authorization_scope_ref")
        _utc_timestamp(self.knowledge_cutoff, "knowledge_cutoff")
        self.policy.validate()
        if len(self.evidence) > self.policy.max_evidence_records:
            raise ValueError("evidence exceeds max_evidence_records")
        evidence_refs: set[str] = set()
        for record in self.evidence:
            record.validate(max_body_chars=self.policy.max_body_chars)
            if record.evidence_ref in evidence_refs:
                raise ValueError("evidence_ref values must be unique")
            evidence_refs.add(record.evidence_ref)
        for hint in self.project_hints:
            hint.validate(evidence_refs)

    def to_dict(self) -> dict[str, object]:
        """Return the versioned request envelope for transport and hashing."""
        return {
            "contract_version": CONTRACT_VERSION,
            "analysis_id": self.analysis_id,
            "authorization_scope_ref": self.authorization_scope_ref,
            "knowledge_cutoff": _timestamp_json(self.knowledge_cutoff),
            "evidence": [record.to_dict() for record in self.evidence],
            "project_hints": [hint.to_dict() for hint in self.project_hints],
            "policy": self.policy.to_dict(),
        }

    def canonical_json(self) -> str:
        """Return deterministic JSON suitable for an idempotency digest."""
        self.validate()
        return json.dumps(self.to_dict(), ensure_ascii=True, sort_keys=True, separators=(",", ":"))

    def request_digest(self) -> str:
        """Return the stable identity of this exact analysis request."""
        return sha256(self.canonical_json().encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class LineageChannelEvidence:
    """One channel's evidence for one reconstructed edge."""

    channel_code: str
    truth_status: str
    score: float | None
    evidence_refs: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        """Return channel evidence with explicit unavailable scores."""
        return {
            "channel_code": self.channel_code,
            "truth_status": self.truth_status,
            "score": self.score,
            "evidence_refs": list(self.evidence_refs),
        }


@dataclass(frozen=True)
class LineageEdgeResult:
    """One inferred parent-to-child relation bounded to submitted evidence."""

    parent_evidence_ref: str
    child_evidence_ref: str
    truth_status: str
    fused_score: float
    channel_evidence: tuple[LineageChannelEvidence, ...]

    def to_dict(self) -> dict[str, object]:
        """Return an edge without introducing database or provider identifiers."""
        return {
            "parent_evidence_ref": self.parent_evidence_ref,
            "child_evidence_ref": self.child_evidence_ref,
            "truth_status": self.truth_status,
            "fused_score": self.fused_score,
            "channel_evidence": [item.to_dict() for item in self.channel_evidence],
        }


@dataclass(frozen=True)
class LineageLimitation:
    """Explicit unavailable or non-authoritative result condition."""

    code: str
    detail: str

    def to_dict(self) -> dict[str, str]:
        """Return the bounded limitation description."""
        return {"code": self.code, "detail": self.detail}


@dataclass(frozen=True)
class LineageAnalysisResult:
    """Serializable analysis result with provenance and explicit limitations."""

    analysis_id: str
    request_digest: str
    knowledge_cutoff: datetime
    edges: tuple[LineageEdgeResult, ...]
    limitations: tuple[LineageLimitation, ...]

    def to_dict(self) -> dict[str, object]:
        """Return the versioned result envelope."""
        return {
            "contract_version": CONTRACT_VERSION,
            "analysis_id": self.analysis_id,
            "request_digest": self.request_digest,
            "knowledge_cutoff": _timestamp_json(self.knowledge_cutoff),
            "edges": [edge.to_dict() for edge in self.edges],
            "limitations": [limitation.to_dict() for limitation in self.limitations],
        }

    def to_json(self) -> str:
        """Return deterministic JSON for a service response or fixture."""
        return json.dumps(self.to_dict(), ensure_ascii=True, sort_keys=True, separators=(",", ":"))


def analyze_lineage(
    request: LineageAnalysisRequest,
    *,
    llm: AdjudicationClient | None = None,
) -> LineageAnalysisResult:
    """Run the existing reconstruction over only evidence known at the cutoff.

    The function is deliberately store-agnostic. A caller owns authorization
    and persistence; this boundary only validates bounded evidence, reuses the
    reviewed reconstruction pipeline, and maps every output edge back to an
    input-owned opaque reference.
    """
    request.validate()
    cutoff = _utc_timestamp(request.knowledge_cutoff, "knowledge_cutoff")
    eligible = [
        record
        for record in request.evidence
        if _utc_timestamp(record.available_at, "evidence.available_at") <= cutoff
    ]
    limitations: list[LineageLimitation] = []
    excluded_count = len(request.evidence) - len(eligible)
    if excluded_count:
        limitations.append(
            LineageLimitation(
                "evidence_after_cutoff_excluded",
                f"{excluded_count} evidence record(s) were unavailable at the knowledge cutoff.",
            )
        )
    if llm is None or not getattr(llm, "available", False):
        limitations.append(
            LineageLimitation(
                "llm_channel_unavailable",
                "The optional LLM channel was unavailable; channel weights were renormalized.",
            )
        )
    if request.project_hints:
        limitations.append(
            LineageLimitation(
                "project_hints_are_non_authoritative",
                "Project hints remain caller evidence and do not change authoritative project status.",
            )
        )

    records = [
        Record(
            record_id=record.evidence_ref,
            group_key=record.group_key,
            label=f"{record.label}\n{record.body_text}".strip(),
            occurred_at=_utc_timestamp(record.occurred_at, "evidence.occurred_at").replace(tzinfo=None),
            secondary_key=record.secondary_key,
        )
        for record in eligible
    ]
    trees = reconstruct(records, llm=llm) if records else []
    edges = [edge for tree in trees for edge in tree.edges]
    eligible_refs = {record.evidence_ref for record in eligible}
    result_edges: list[LineageEdgeResult] = []
    for edge in edges:
        if edge.parent_id not in eligible_refs or edge.child_id not in eligible_refs:
            continue
        channel_evidence = tuple(
            LineageChannelEvidence(
                channel_code=channel,
                truth_status="inferred",
                score=score,
                evidence_refs=(edge.parent_id, edge.child_id),
            )
            for channel, score in sorted(edge.channel_scores.items())
        )
        result_edges.append(
            LineageEdgeResult(
                parent_evidence_ref=edge.parent_id,
                child_evidence_ref=edge.child_id,
                truth_status="inferred",
                fused_score=edge.fused_score,
                channel_evidence=channel_evidence,
            )
        )
    return LineageAnalysisResult(
        analysis_id=request.analysis_id,
        request_digest=request.request_digest(),
        knowledge_cutoff=cutoff,
        edges=tuple(result_edges),
        limitations=tuple(limitations),
    )
