"""Flatten ``reconstruct()`` trees into the rows ``post_lineage_edge`` stores.

The reconstruction algorithm stays in ``reconstruct.py``. This module is
only the persistence contract: one ``Edge`` becomes one
``(parent_post_id, child_post_id, fused_score)`` row. Seed scripts and a
future rebuild endpoint share this so they cannot drift from what the
Event Lineage panel reads.
"""

from __future__ import annotations

from collections.abc import Sequence

from .adjudication_client import AdjudicationClient
from .models import Edge, Record
from .reconstruct import reconstruct


def lineage_edge_specs(records: Sequence[Record], *, llm: AdjudicationClient | None = None) -> list[Edge]:
    """Run reconstruct and return every resulting parent→child edge.

    Callers persist these as ``post_lineage_edge`` rows. Record ids must
    already be the ids the database will store (UUIDs for product posts,
    fixture ids for the library-only demo) -- this function does not
    invent or rewrite identifiers.

    ``llm`` defaults to ``None``, which ``reconstruct()`` treats as the
    unavailable :class:`~lineageweave.adjudication_client.NullAdjudicationClient`
    (the llm channel is then dropped and the rest renormalized, not
    faked) -- callers that want the highest-weighted reasoning channel
    actually contributing to real reconstructions must pass a real one.
    """
    trees = reconstruct(list(records), llm=llm)
    return [edge for tree in trees for edge in tree.edges]
