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

from .adjudication_client import AdjudicationClient, NullAdjudicationClient
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
from .reconstruct import active_weights, reconstruct


def _contract_error(code: str, message: str, field: str | None = None) -> None:
    """Raise a stable execution-time contract error."""

    raise LineageContractError(code, message, field=field)


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
) -> tuple[AdjudicationClient, str]:
    """Apply the explicit LLM admission policy and return its result status."""

    if not request.policy.allow_llm:
        return NullAdjudicationClient(), "not_requested"
    if llm is None or not getattr(llm, "available", False):
        return NullAdjudicationClient(), "unavailable"
    return llm, "completed"


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


def _pair_evaluation_count(
    records: tuple[LineageEvidenceRecord, ...],
    candidate_window: int,
) -> int:
    """Count candidate-parent evaluations before running any channel."""

    counts: dict[str, int] = defaultdict(int)
    for record in records:
        counts[record.group_ref] += 1
    return sum(
        sum(
            min(index, candidate_window)
            for index in range(record_count)
        )
        for record_count in counts.values()
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


def _core_records(
    records: tuple[LineageEvidenceRecord, ...],
) -> list[Record]:
    """Convert contract records to deterministic core reconstruction records."""

    ordered = sorted(
        records,
        key=lambda item: (
            item.group_ref,
            item.occurred_at,
            item.evidence_ref,
        ),
    )
    return [
        Record(
            record_id=record.evidence_ref,
            group_key=record.group_ref,
            label=record.label,
            occurred_at=record.occurred_at,
            secondary_key=record.secondary_key or "",
        )
        for record in ordered
    ]


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
) -> list[LineageEdgeResult]:
    """Run the core kernel and project inferred edge/channel evidence."""

    if not records:
        return []
    weights = active_weights(llm)
    trees = reconstruct(
        _core_records(records),
        llm=llm,
        candidate_window=request.policy.candidate_window,
        min_fused_score=request.policy.minimum_fused_score,
    )
    return [
        LineageEdgeResult(
            parent_evidence_ref=edge.parent_id,
            child_evidence_ref=edge.child_id,
            relation_type_code="reconstructed_continuation",
            truth_status_code="inferred",
            fused_score=float(edge.fused_score),
            channel_evidence=_channel_evidence(
                edge.channel_scores,
                weights,
            ),
        )
        for tree in trees
        for edge in tree.edges
    ]


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
    llm: AdjudicationClient | None = None,
) -> LineageAnalysisResult:
    """Analyze bounded caller evidence and return a deterministic result.

    The function performs no persistence or network access itself. An optional
    client is used only when ``request.policy.allow_llm`` is true and the
    supplied client explicitly reports availability.
    """

    validated = _validated_request(request)
    _validate_explicit_parent_relations(validated.records)
    included, excluded = _included_records(validated)
    _enforce_pair_budget(included, validated)
    selected_llm, llm_status = _selected_llm(validated, llm)

    inferred = _inferred_edges(
        included,
        selected_llm,
        validated,
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
                    item.child_evidence_ref,
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
