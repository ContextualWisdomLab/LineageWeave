"""LineageWeave: reconstruct evidence-bounded lineage DAGs.

LineageWeave fuses independent signals such as temporal proximity, shared
keys, text similarity, and optional adjudication into per-record parent choices.
See ``ARCHITECTURE.md`` and ``docs/lineage-bi-research-notes.md`` for the
product and research boundaries.
"""

from .affiliate_tree import build_affiliate_forest
from .corporate_hierarchy_resolution import resolve_corporate_entity
from .entity_relationship_classification import OrganizationRelationship
from .knowledge_graph import random_walk_with_restart, select_related_nodes
from .lineage_persistence import lineage_edge_specs
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
    "ChatAnswer",
    "Edge",
    "NARUON_CALENDAR_MEDIA_TYPE",
    "NARUON_CALENDAR_SCHEMA_VERSION",
    "NaruonCalendarContractError",
    "NaruonCalendarOccurrence",
    "NaruonCalendarPage",
    "NaruonCalendarProjectionClient",
    "OrganizationRelationship",
    "PROV",
    "PROV_CLASSES",
    "PROV_QUALIFICATIONS",
    "PROV_RELATIONS",
    "PROV_RECOMMENDED_INVERSES",
    "PostSummary",
    "ProvAssertion",
    "ProvGraph",
    "ProvLiteral",
    "ProvValidationError",
    "Record",
    "Tree",
    "build_affiliate_forest",
    "cited_post_summaries",
    "lineage_edge_specs",
    "parse_naruon_calendar_page",
    "random_walk_with_restart",
    "reconstruct",
    "resolve_corporate_entity",
    "select_related_nodes",
    "sentence_excerpts",
]

__version__ = "2.12.19"
