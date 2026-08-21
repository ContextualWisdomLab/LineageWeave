"""LineageWeave: reconstructs git-branch-style lineage DAGs from scattered
short records by fusing independent, individually-weak signals (temporal
proximity, shared grouping keys, text similarity, and optional LLM
adjudication) into a single per-record parent choice.

See ARCHITECTURE.md for the design and docs/lineage-bi-research-notes.md
for the literature this design is grounded in.
"""

from .affiliate_tree import build_affiliate_forest
from .corporate_hierarchy_resolution import resolve_corporate_entity
from .entity_relationship_classification import OrganizationRelationship
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
from .knowledge_graph import random_walk_with_restart, select_related_nodes
from .lineage_persistence import lineage_edge_specs
from .models import Edge, Record, Tree
from .post_chat import ChatAnswer, cited_post_summaries
from .post_summary import PostSummary
from .prov_o import (
    PROV,
    PROV_CLASSES,
    PROV_QUALIFICATIONS,
    PROV_RELATIONS,
    PROV_RECOMMENDED_INVERSES,
    ProvAssertion,
    ProvGraph,
    ProvLiteral,
    ProvValidationError,
)
from .reconstruct import reconstruct
from .voc_evidence import sentence_excerpts

__all__ = [
    "CONTRACT_VERSION",
    "ChannelEvidence",
    "ChatAnswer",
    "Edge",
    "ExplicitParent",
    "LineageAnalysisPolicy",
    "LineageAnalysisRequest",
    "LineageAnalysisResult",
    "LineageContractError",
    "LineageEdgeResult",
    "LineageEvidenceRecord",
    "LineageLimitation",
    "OrganizationRelationship",
    "PROV",
    "PROV_CLASSES",
    "PROV_QUALIFICATIONS",
    "PROV_RELATIONS",
    "PROV_RECOMMENDED_INVERSES",
    "PostSummary",
    "ProjectProjection",
    "ProvAssertion",
    "ProvGraph",
    "ProvLiteral",
    "ProvValidationError",
    "Record",
    "Tree",
    "analyze_external_lineage",
    "build_affiliate_forest",
    "cited_post_summaries",
    "lineage_edge_specs",
    "parse_lineage_analysis_request",
    "random_walk_with_restart",
    "reconstruct",
    "request_digest",
    "resolve_corporate_entity",
    "result_digest",
    "select_related_nodes",
    "sentence_excerpts",
    "serialize_lineage_analysis_request",
    "serialize_lineage_analysis_result",
]

__version__ = "2.16.0"
