"""Execute the external lineage contract through the core reconstruction kernel.

This adapter is deliberately store-agnostic. It accepts an already parsed,
caller-authorized request, applies available-time cutoff rules, invokes the
existing deterministic/optional-LLM reconstruction kernel, and returns only
opaque caller references plus evidence-bounded result metadata.
"""

from __future__ import annotations

import math
from collections import defaultdict
from dataclasses import replace

from .adjudication_client import (
    AdjudicationClient,
    NullAdjudicationClient,
)
from .external_lineage_contract import (
    CONTRACT_VERSION,
    ChannelEvidence,
    LineageAnalysisRequest,
    LineageAnalysisResult,
    LineageContractError,
    LineageEdgeResult,
    LineageEvidenceRecord,
    LineageLimitation,
    ProjectProjection,
    parse_lineage_analysis_request,
    result_digest,
    serialize_lineage_analysis_request,
)
from .models import Record
from .reconstruct import _best_parent

_WEIGHT_CHANNELS = frozenset({"temporal", "secondary_key", "text", "llm"})
_REQUIRED_WEIGHT_CHANNELS = frozenset({"temporal", "secondary_key", "text"})


def _contract_error(code: str, message: str, field: str | None = None) -> None:
    """Raise a stable execution-time contract error."""

    raise LineageContractError(code, message, field=field)


def _validated_channel_weights(weights: dict[str, float]) -> dict[str, float]:
    """Validate a calibrated convex weight vector without repairing it."""
    channels = set(weights)
    if not _REQUIRED_WEIGHT_CHANNELS <= channels or not channels <= _WEIGHT_CHANNELS:
        _contract_error(
            "invalid_channel_weights",
            "weights must contain the three core channels and only supported channels",
            "channel_weights",
        )
    values = tuple(weights.values())
    if any(
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not math.isfinite(float(value))
        or float(value) <= 0.0
        for value in values
    ) or not math.isclose(sum(values), 1.0, abs_tol=1e-9):
        _contract_error(
            "invalid_channel_weights",
            "weights must be positive finite values summing to one",
            "channel_weights",
        )
    return {channel: float(weight) for channel, weight in weights.items()}


class _BoundedAdjudicationClient:
    """Keep provider channel scores inside the fusion contract boundary."""

    available = True

    def __init__(self, client: AdjudicationClient) -> None:
        """Wrap one available client without changing its provider behavior."""

        self._client = client

    def judge(self, candidate_label: str, record_label: str) -> float:
        """Return one finite unit-interval score or fail with a stable code."""

        try:
            score = self._client.judge(candidate_label, record_label)
        except Exception as exc:
            raise LineageContractError(
                "llm_channel_error",
                "LLM channel returned an unusable provider response",
                field="llm",
            ) from exc
        if isinstance(score, bool) or not isinstance(score, (int, float)):
            _contract_error(
                "channel_score_out_of_bounds",
                "LLM channel score must be finite and within 0..1",
                "llm",
            )
        number = float(score)
        if not math.isfinite(number) or not 0.0 <= number <= 1.0:
            _contract_error(
                "channel_score_out_of_bounds",
                "LLM channel score must be finite and within 0..1",
                "llm",
            )
        return number


def _validated_request(request: LineageAnalysisRequest) -> LineageAnalysisRequest:
    """Round-trip a dataclass through the public parser before execution."""

    return parse_lineage_analysis_request(
        serialize_lineage_analysis_request(request)
    )


def _validate_explicit_parent_relations(
    records: tuple[LineageEvidenceRecord, ...],
) -> None:
    """Validate caller-observed parent relations before cutoff filtering."""

    by_ref = {record.evidence_ref: record for record in records}
    for child in records:
        explicit = child.explicit_parent
        if explicit is None:
            continue
        if explicit.evidence_ref == child.evidence_ref:
            _contract_error(
                "explicit_parent_self_reference",
                "an evidence record cannot be its own parent",
                child.evidence_ref,
            )
        parent = by_ref.get(explicit.evidence_ref)
        if parent is None:
            _contract_error(
                "explicit_parent_missing",
                "explicit parent is absent from the request",
                child.evidence_ref,
            )
        if parent.group_ref != child.group_ref:
            _contract_error(
                "explicit_parent_group_mismatch",
                "explicit parent and child must share one group",
                child.evidence_ref,
            )
        if parent.occurred_at > child.occurred_at:
            _contract_error(
                "explicit_parent_after_child",
                "explicit parent occurs after the child",
                child.evidence_ref,
            )

    parent_by_child = {
        child.evidence_ref: child.explicit_parent.evidence_ref
        for child in records
        if child.explicit_parent is not None
    }
    for start_ref in parent_by_child:
        current_ref = start_ref
        visited: set[str] = set()
        while current_ref in parent_by_child:
            if current_ref in visited:
                _contract_error(
                    "explicit_parent_cycle",
                    "explicit parent relations must form an acyclic graph",
                    start_ref,
                )
            visited.add(current_ref)
            current_ref = parent_by_child[current_ref]


def _selected_llm(
    request: LineageAnalysisRequest,
    llm: AdjudicationClient | None,
    channel_weights: dict[str, float],
) -> tuple[AdjudicationClient, str]:
    """Apply the explicit LLM admission policy and return its result status."""

    if not request.policy.allow_llm:
        return NullAdjudicationClient(), "not_requested"
    if "llm" not in channel_weights or llm is None or not getattr(llm, "available", False):
        return NullAdjudicationClient(), "unavailable"
    return _BoundedAdjudicationClient(llm), "completed"


def _validate_active_channel_weights(
    llm: AdjudicationClient, channel_weights: dict[str, float]
) -> None:
    """Require the calibrated vector to match the channels actually executed."""

    if ("llm" in channel_weights) != bool(getattr(llm, "available", False)):
        _contract_error(
            "channel_weight_set_mismatch",
            "calibrated weights must exactly match the active channels",
            "channel_weights",
        )


def _included_records(
    request: LineageAnalysisRequest,
) -> tuple[
    tuple[LineageEvidenceRecord, ...],
    tuple[LineageEvidenceRecord, ...],
]:
    """Partition evidence by available time, not occurrence time."""

    if request.knowledge_cutoff is None:
        return request.records, ()
    included = tuple(
        record
        for record in request.records
        if record.available_at <= request.knowledge_cutoff
    )
    excluded = tuple(
        record
        for record in request.records
        if record.available_at > request.knowledge_cutoff
    )
    return included, excluded


def _ordered_contract_groups(
    records: tuple[LineageEvidenceRecord, ...],
) -> tuple[tuple[LineageEvidenceRecord, ...], ...]:
    """Return deterministic groups ordered by time and opaque reference."""

    grouped: dict[str, list[LineageEvidenceRecord]] = defaultdict(list)
    for record in records:
        grouped[record.group_ref].append(record)
    return tuple(
        tuple(
            sorted(
                grouped[group_ref],
                key=lambda item: (item.occurred_at, item.evidence_ref),
            )
        )
        for group_ref in sorted(grouped)
    )


def _pair_evaluation_count(
    records: tuple[LineageEvidenceRecord, ...],
    candidate_window: int,
) -> int:
    """Count only candidate pairs that require inferred parent selection."""

    return sum(
        min(index, candidate_window)
        for group_records in _ordered_contract_groups(records)
        for index, record in enumerate(group_records)
        if record.explicit_parent is None
    )


def _enforce_pair_budget(
    records: tuple[LineageEvidenceRecord, ...],
    request: LineageAnalysisRequest,
) -> int:
    """Reject excess pair work before optional LLM/provider activity."""

    pair_count = _pair_evaluation_count(
        records,
        request.policy.candidate_window,
    )
    if pair_count > request.policy.maximum_pair_evaluations:
        _contract_error(
            "pair_evaluation_budget_exceeded",
            "candidate-pair work exceeds the declared maximum",
            "policy.maximum_pair_evaluations",
        )
    return pair_count


def _core_record(record: LineageEvidenceRecord) -> Record:
    """Convert one contract record to the core reconstruction shape."""

    return Record(
        record_id=record.evidence_ref,
        group_key=record.group_ref,
        label=record.label,
        occurred_at=record.occurred_at,
        secondary_key=record.secondary_key or "",
    )


def _channel_evidence(
    channel_scores: dict[str, float],
    weights: dict[str, float],
) -> tuple[ChannelEvidence, ...]:
    """Project finite active scores with their normalized contributions."""

    projected: list[ChannelEvidence] = []
    for channel_code in sorted(channel_scores):
        score = float(channel_scores[channel_code])
        weight = float(weights[channel_code])
        contribution = score * weight
        values = (score, weight, contribution)
        if not all(
            math.isfinite(value) and 0.0 <= value <= 1.0
            for value in values
        ):
            _contract_error(
                "channel_score_out_of_bounds",
                "channel values must be finite within 0..1",
                channel_code,
            )
        projected.append(
            ChannelEvidence(
                channel_code,
                score,
                weight,
                contribution,
            )
        )
    return tuple(projected)


def _inferred_edges(
    records: tuple[LineageEvidenceRecord, ...],
    llm: AdjudicationClient,
    request: LineageAnalysisRequest,
    channel_weights: dict[str, float],
) -> list[LineageEdgeResult]:
    """Select inferred parents without rescoring explicit observed children."""

    if not records:
        return []
    weights = channel_weights
    edges: list[LineageEdgeResult] = []
    for group_records in _ordered_contract_groups(records):
        core_records = [_core_record(record) for record in group_records]
        for index, source_record in enumerate(group_records):
            if source_record.explicit_parent is not None:
                continue
            candidates = core_records[
                max(0, index - request.policy.candidate_window) : index
            ]
            parent_choice = _best_parent(
                core_records[index],
                candidates,
                llm,
                weights,
                request.policy.minimum_fused_score,
            )
            if parent_choice is None:
                continue
            parent, fused_score, channel_scores = parent_choice
            edges.append(
                LineageEdgeResult(
                    parent_evidence_ref=parent.record_id,
                    child_evidence_ref=source_record.evidence_ref,
                    relation_type_code="reconstructed_continuation",
                    truth_status_code="inferred",
                    fused_score=float(fused_score),
                    channel_evidence=_channel_evidence(
                        channel_scores,
                        weights,
                    ),
                )
            )
    return edges


def _explicit_edges(
    included: tuple[LineageEvidenceRecord, ...],
) -> tuple[
    list[LineageEdgeResult],
    set[str],
    list[LineageLimitation],
]:
    """Project included caller-observed parent relations ahead of inference."""

    included_refs = {record.evidence_ref for record in included}
    edges: list[LineageEdgeResult] = []
    explicit_children: set[str] = set()
    limitations: list[LineageLimitation] = []
    for child in included:
        explicit = child.explicit_parent
        if explicit is None:
            continue
        explicit_children.add(child.evidence_ref)
        if explicit.evidence_ref not in included_refs:
            limitations.append(
                LineageLimitation(
                    "explicit_parent_after_cutoff",
                    child.evidence_ref,
                    (
                        "The caller-observed parent was unavailable at "
                        "the requested cutoff."
                    ),
                )
            )
            continue
        edges.append(
            LineageEdgeResult(
                parent_evidence_ref=explicit.evidence_ref,
                child_evidence_ref=child.evidence_ref,
                relation_type_code=explicit.relation_code,
                truth_status_code="observed",
                fused_score=1.0,
                channel_evidence=(
                    ChannelEvidence(
                        explicit.relation_code,
                        1.0,
                        1.0,
                        1.0,
                    ),
                ),
            )
        )
    return edges, explicit_children, limitations


def _project_groups(
    records: tuple[LineageEvidenceRecord, ...],
) -> tuple[ProjectProjection, ...]:
    """Group included project evidence without crossing caller groups."""

    grouped: dict[tuple[str, str], list[str]] = defaultdict(list)
    for record in records:
        if record.project_ref is not None:
            grouped[(record.group_ref, record.project_ref)].append(
                record.evidence_ref
            )
    return tuple(
        ProjectProjection(
            group_ref,
            project_ref,
            tuple(sorted(evidence_refs)),
            "proposed",
        )
        for (group_ref, project_ref), evidence_refs in sorted(
            grouped.items()
        )
    )


def analyze_external_lineage(
    request: LineageAnalysisRequest,
    *,
    channel_weights: dict[str, float],
    llm: AdjudicationClient | None = None,
) -> LineageAnalysisResult:
    """Analyze bounded caller evidence and return a deterministic result.

    The function performs no persistence or network access itself. An optional
    client is used only when ``request.policy.allow_llm`` is true and the
    supplied client explicitly reports availability. ``channel_weights`` must
    come from the caller's ADR-governed calibrated weight loader; this adapter
    deliberately has no invented fallback.
    """

    validated = _validated_request(request)
    validated_weights = _validated_channel_weights(channel_weights)
    _validate_explicit_parent_relations(validated.records)
    included, excluded = _included_records(validated)
    _enforce_pair_budget(included, validated)
    selected_llm, llm_status = _selected_llm(validated, llm, validated_weights)
    _validate_active_channel_weights(selected_llm, validated_weights)

    inferred = _inferred_edges(
        included,
        selected_llm,
        validated,
        validated_weights,
    )
    explicit, explicit_children, explicit_limitations = _explicit_edges(
        included
    )
    edges = [
        edge
        for edge in inferred
        if edge.child_evidence_ref not in explicit_children
    ]
    edges.extend(explicit)

    limitations = [
        LineageLimitation(
            "evidence_after_cutoff_excluded",
            record.evidence_ref,
            (
                "Evidence was first available after the requested "
                "knowledge cutoff."
            ),
        )
        for record in excluded
    ]
    limitations.extend(explicit_limitations)

    edge_order = {
        record.evidence_ref: (record.group_ref, record.occurred_at, record.evidence_ref)
        for record in included
    }
    result = LineageAnalysisResult(
        contract_version=CONTRACT_VERSION,
        analysis_id=validated.analysis_id,
        analysis_scope_code=validated.analysis_scope_code,
        knowledge_cutoff=validated.knowledge_cutoff,
        included_evidence_refs=tuple(
            sorted(record.evidence_ref for record in included)
        ),
        excluded_evidence_refs=tuple(
            sorted(record.evidence_ref for record in excluded)
        ),
        llm_status_code=llm_status,  # type: ignore[arg-type]
        edges=tuple(
            sorted(
                edges,
                key=lambda item: (
                    edge_order[item.child_evidence_ref],
                    item.parent_evidence_ref,
                    item.relation_type_code,
                ),
            )
        ),
        project_projections=_project_groups(included),
        limitations=tuple(
            sorted(
                limitations,
                key=lambda item: (
                    item.limitation_code,
                    item.evidence_ref or "",
                    item.message,
                ),
            )
        ),
        result_digest="",
    )
    return replace(
        result,
        result_digest=result_digest(result),
    )
