"""LineageWeave: reconstruct evidence-bounded lineage DAGs.

LineageWeave fuses independent signals such as temporal proximity, shared
keys, text similarity, and optional adjudication into per-record parent choices.
See ``ARCHITECTURE.md`` and ``docs/lineage-bi-research-notes.md`` for the
product and research boundaries.
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
from .lineage_persistence import (
    CHANNEL_EVIDENCE_TOLERANCE,
    lineage_edge_specs,
    rank_channel_evidence,
    reconstruction_version,
)
from .models import Edge, Record, Tree
from .naruon_calendar_projection import (
    NARUON_CALENDAR_MEDIA_TYPE,
    NARUON_CALENDAR_SCHEMA_VERSION,
    NaruonCalendarContractError,
    NaruonCalendarOccurrence,
    NaruonCalendarPage,
    NaruonCalendarProjectionClient,
    parse_naruon_calendar_page,
)
from .naruon_calendar_workspace import (
    NARUON_CALENDAR_UNAVAILABLE_NEXT_ACTION,
    NaruonCalendarWorkspaceEvent,
    NaruonCalendarWorkspaceResult,
    build_workspace_naruon_client,
    default_calendar_window,
    load_observed_calendar_events,
    occurrence_to_workspace_event,
)
from .post_chat import ChatAnswer, cited_post_summaries
from .post_summary import PostSummary
from .prov_o import (
    PROV,
    PROV_CLASSES,
    PROV_QUALIFICATIONS,
    PROV_RECOMMENDED_INVERSES,
    PROV_RELATIONS,
    ProvAssertion,
    ProvGraph,
    ProvLiteral,
    ProvValidationError,
)
from .reconstruct import reconstruct
from .voc_evidence import sentence_excerpts

__all__ = [
    "CHANNEL_EVIDENCE_TOLERANCE",
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
    "NARUON_CALENDAR_MEDIA_TYPE",
    "NARUON_CALENDAR_SCHEMA_VERSION",
    "NARUON_CALENDAR_UNAVAILABLE_NEXT_ACTION",
    "NaruonCalendarContractError",
    "NaruonCalendarOccurrence",
    "NaruonCalendarPage",
    "NaruonCalendarProjectionClient",
    "NaruonCalendarWorkspaceEvent",
    "NaruonCalendarWorkspaceResult",
    "PROV",
    "PROV_CLASSES",
    "PROV_QUALIFICATIONS",
    "PROV_RECOMMENDED_INVERSES",
    "PROV_RELATIONS",
    "ChatAnswer",
    "Edge",
    "OrganizationRelationship",
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
    "build_workspace_naruon_client",
    "cited_post_summaries",
    "default_calendar_window",
    "lineage_edge_specs",
    "load_observed_calendar_events",
    "occurrence_to_workspace_event",
    "parse_lineage_analysis_request",
    "parse_naruon_calendar_page",
    "random_walk_with_restart",
    "rank_channel_evidence",
    "reconstruct",
    "reconstruction_version",
    "request_digest",
    "resolve_corporate_entity",
    "result_digest",
    "select_related_nodes",
    "sentence_excerpts",
    "serialize_lineage_analysis_request",
    "serialize_lineage_analysis_result",
]

__version__ = "2.30.0"
