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
    "ChatAnswer",
    "Edge",
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
    "random_walk_with_restart",
    "reconstruct",
    "resolve_corporate_entity",
    "select_related_nodes",
    "sentence_excerpts",
]

__version__ = "2.10.2"
