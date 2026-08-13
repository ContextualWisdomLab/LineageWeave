"""LineageWeave: reconstructs git-branch-style lineage DAGs from scattered
short records by fusing independent, individually-weak signals (temporal
proximity, shared grouping keys, text similarity, and optional LLM
adjudication) into a single per-record parent choice.

See ARCHITECTURE.md for the design and docs/lineage-bi-research-notes.md
for the literature this design is grounded in.
"""

from .knowledge_graph import random_walk_with_restart, select_related_nodes
from .models import Edge, Record, Tree
from .reconstruct import reconstruct

__all__ = [
    "Edge",
    "Record",
    "Tree",
    "random_walk_with_restart",
    "reconstruct",
    "select_related_nodes",
]

__version__ = "0.8.0"
