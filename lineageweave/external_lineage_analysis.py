"""Execute the external lineage contract through the core reconstruction kernel.

This adapter is deliberately store-agnostic. It accepts an already parsed,
caller-authorized request, applies available-time cutoff rules, invokes the
existing deterministic/optional-LLM reconstruction kernel, and returns only
opaque caller references plus evidence-bounded result metadata.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import replace

from .adjudication_client import AdjudicationClient
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


def _has_inference_candidate(
    records: tuple[LineageEvidenceRecord, ...],
) -> bool:
    """Return whether a same-group predecessor could support inference."""

    return any(
        index > 0 and record.explicit_parent is None
        for group_records in _ordered_contract_groups(records)
        for index, record in enumerate(group_records)
    )


def _pair_evaluation_count(
    records: tuple[LineageEvidenceRecord, ...],
    candidate_window: int,
) -> int:
    """Count only candidate pairs that require inferred parent selection."""

    included_refs = {record.evidence_ref for record in records}
    explicit_children_by_parent: dict[str, set[str]] = defaultdict(set)
    for record in records:
        if (
            record.explicit_parent is not None
            and record.explicit_parent.evidence_ref in included_refs
        ):
            explicit_children_by_parent[
                record.explicit_parent.evidence_ref
            ].add(record.evidence_ref)

    def explicit_descendants(evidence_ref: str) -> set[str]:
        """Return observed descendants excluded from the pair-work budget."""

        descendants: set[str] = set()
        pending = list(explicit_children_by_parent.get(evidence_ref, ()))
        while pending:
            descendant = pending.pop()
            if descendant in descendants:
                continue
            descendants.add(descendant)
            pending.extend(explicit_children_by_parent.get(descendant, ()))
        return descendants

    pair_count = 0
    for group_records in _ordered_contract_groups(records):
        for index, record in enumerate(group_records):
            if record.explicit_parent is not None:
                continue
            candidates = group_records[max(0, index - candidate_window) : index]
            descendants = explicit_descendants(record.evidence_ref)
            pair_count += sum(
                candidate.evidence_ref not in descendants
                for candidate in candidates
            )
    return pair_count


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
    weight_estimate: object | None = None,
) -> LineageAnalysisResult:
    """Analyze bounded caller evidence and return a deterministic result.

    The function performs no persistence or network access itself. An optional
    Inferred reconstruction stays unavailable until an accepted owner artifact
    is published. The optional arguments remain for source compatibility but
    cannot activate local scoring or provider calls.
    """

    validated = _validated_request(request)
    _validate_explicit_parent_relations(validated.records)
    included, excluded = _included_records(validated)
    _enforce_pair_budget(included, validated)
    del llm, weight_estimate
    llm_status = "unavailable" if validated.policy.allow_llm else "not_requested"
    explicit, explicit_children, explicit_limitations = _explicit_edges(
        included
    )
    del explicit_children
    edges = explicit

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
    if _has_inference_candidate(included):
        limitations.append(
            LineageLimitation(
                "channel_weights_unavailable",
                None,
                (
                    "No provenance-bearing psychometric channel-weight estimate "
                    "was supplied, so inferred continuation edges are unavailable."
                ),
            )
        )
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
