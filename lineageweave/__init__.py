"""LineageWeave: reconstructs git-branch-style lineage DAGs from scattered
short records by fusing independent, individually-weak signals (temporal
proximity, shared grouping keys, text similarity, and optional LLM
adjudication) into a single per-record parent choice.

See ARCHITECTURE.md for the design and docs/lineage-bi-research-notes.md
for the literature this design is grounded in.
"""

from .corporate_hierarchy_resolution import resolve_corporate_entity
from .entity_relationship_classification import OrganizationRelationship
from .knowledge_graph import random_walk_with_restart, select_related_nodes
from .lineage_persistence import lineage_edge_specs
from .models import Edge, Record, Tree
from .post_chat import ChatAnswer
from .post_summary import PostSummary
from .reconstruct import reconstruct

__all__ = [
    "ChatAnswer",
    "Edge",
    "OrganizationRelationship",
    "PostSummary",
    "Record",
    "Tree",
    "lineage_edge_specs",
    "random_walk_with_restart",
    "reconstruct",
    "resolve_corporate_entity",
    "select_related_nodes",
]

__version__ = "0.13.0"
