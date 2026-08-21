"""Stable public package surface for external lineage consumers."""

from .external_lineage_analysis import analyze_external_lineage
from .external_lineage_contract import (
    CONTRACT_VERSION,
    ChannelEvidence,
    ExplicitParent,
    LineageAnalysisPolicy,
    LineageAnalysisRequest,
    LineageAnalysisResult,
    LineageContractError,
    LineageEdgeResult,
    LineageEvidenceRecord,
    LineageLimitation,
    ProjectProjection,
    parse_lineage_analysis_request,
    request_digest,
    result_digest,
    serialize_lineage_analysis_request,
    serialize_lineage_analysis_result,
)

__all__ = [
    "CONTRACT_VERSION",
    "ChannelEvidence",
    "ExplicitParent",
    "LineageAnalysisPolicy",
    "LineageAnalysisRequest",
    "LineageAnalysisResult",
    "LineageContractError",
    "LineageEdgeResult",
    "LineageEvidenceRecord",
    "LineageLimitation",
    "ProjectProjection",
    "analyze_external_lineage",
    "parse_lineage_analysis_request",
    "request_digest",
    "result_digest",
    "serialize_lineage_analysis_request",
    "serialize_lineage_analysis_result",
]
