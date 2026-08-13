"""LineageWeave: reconstructs git-branch-style lineage DAGs from scattered
short records by fusing independent, individually-weak signals (temporal
proximity, shared grouping keys, text similarity, and optional LLM
adjudication) into a single per-record parent choice.

See ARCHITECTURE.md for the design and docs/lineage-bi-research-notes.md
for the literature this design is grounded in.
"""

from .models import Edge, Record, Tree
from .reconstruct import reconstruct

__all__ = ["Edge", "Record", "Tree", "reconstruct"]

__version__ = "0.3.0"
