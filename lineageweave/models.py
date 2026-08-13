"""Data shapes shared across the LineageWeave pipeline.

Deliberately generic field names (``group_key``, ``label``, ``occurred_at``)
so any source of short, timestamped, loosely-grouped records can be adapted
into a :class:`Record` -- this module has no knowledge of any specific
upstream schema.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass(frozen=True)
class Record:
    """One node to be placed in the lineage DAG.

    Attributes:
        record_id: Stable, unique identifier for this record.
        group_key: Coarse grouping key (e.g. a customer or account id) that
            bounds which other records are even considered as candidate
            parents. Every :class:`Tree` in the output corresponds to one
            distinct ``group_key``.
        label: Short human-readable text (a title/subject line) used by the
            text-similarity channel and shown in the UI.
        occurred_at: When the record was created; lineage edges only ever
            point from an earlier record to a later one.
        secondary_key: An optional finer-grained grouping key (e.g. a
            project code) that, when it matches between two records, is a
            strong same-thread signal independent of text similarity.
    """

    record_id: str
    group_key: str
    label: str
    occurred_at: datetime
    secondary_key: str = ""


@dataclass(frozen=True)
class Edge:
    """One reconstructed lineage edge: ``child`` follows from ``parent``."""

    parent_id: str
    child_id: str
    fused_score: float
    channel_scores: dict[str, float] = field(default_factory=dict)


@dataclass(frozen=True)
class Tree:
    """One reconstructed lineage tree for a single ``group_key``.

    ``roots`` are records with no reconstructed parent (the start of a
    thread); ``children_of`` maps a record id to the ids of records that
    follow from it, so a branch point is any id with ``len(children) >= 2``.
    """

    group_key: str
    records: dict[str, Record]
    edges: list[Edge]
    roots: list[str]
    children_of: dict[str, list[str]]

    def branch_points(self) -> list[str]:
        """Record ids with two or more children -- where the DAG forks."""
        return [record_id for record_id, kids in self.children_of.items() if len(kids) >= 2]
