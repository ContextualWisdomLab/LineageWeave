"""Allen (1983) closed interval relations for Event Lineage edges.

Reconstruct already refuses a parent that occurred after its child.
This module names the Allen relation between two dated windows so a buyer can
see *how* they relate in time, not only that a fused score attached them. A
post is a degenerate point interval on its observed ``created_at`` day. Mutable
ticket dates are not Event Lineage evidence.

Does not invent a theta, a fused score, or a lineage parent.
"""

from __future__ import annotations

from datetime import date, datetime, timezone

INTERVAL_BEFORE = "interval_before"
INTERVAL_AFTER = "interval_after"
INTERVAL_MEETS = "interval_meets"
INTERVAL_MET_BY = "interval_met_by"
INTERVAL_OVERLAPS = "interval_overlaps"
INTERVAL_OVERLAPPED_BY = "interval_overlapped_by"
INTERVAL_STARTS = "interval_starts"
INTERVAL_STARTED_BY = "interval_started_by"
INTERVAL_DURING = "interval_during"
INTERVAL_CONTAINS = "interval_contains"
INTERVAL_FINISHES = "interval_finishes"
INTERVAL_FINISHED_BY = "interval_finished_by"
INTERVAL_EQUALS = "interval_equals"

INTERVAL_RELATION_CODES: tuple[str, ...] = (
    INTERVAL_BEFORE,
    INTERVAL_AFTER,
    INTERVAL_MEETS,
    INTERVAL_MET_BY,
    INTERVAL_OVERLAPS,
    INTERVAL_OVERLAPPED_BY,
    INTERVAL_STARTS,
    INTERVAL_STARTED_BY,
    INTERVAL_DURING,
    INTERVAL_CONTAINS,
    INTERVAL_FINISHES,
    INTERVAL_FINISHED_BY,
    INTERVAL_EQUALS,
)

INTERVAL_RELATION_LABELS: dict[str, str] = {
    INTERVAL_BEFORE: "Before",
    INTERVAL_AFTER: "After",
    INTERVAL_MEETS: "Meets",
    INTERVAL_MET_BY: "Met by",
    INTERVAL_OVERLAPS: "Overlaps",
    INTERVAL_OVERLAPPED_BY: "Overlapped by",
    INTERVAL_STARTS: "Starts",
    INTERVAL_STARTED_BY: "Started by",
    INTERVAL_DURING: "During",
    INTERVAL_CONTAINS: "Contains",
    INTERVAL_FINISHES: "Finishes",
    INTERVAL_FINISHED_BY: "Finished by",
    INTERVAL_EQUALS: "Equals",
}

INTERVAL_RELATION_INVERSE: dict[str, str] = {
    INTERVAL_BEFORE: INTERVAL_AFTER,
    INTERVAL_AFTER: INTERVAL_BEFORE,
    INTERVAL_MEETS: INTERVAL_MET_BY,
    INTERVAL_MET_BY: INTERVAL_MEETS,
    INTERVAL_OVERLAPS: INTERVAL_OVERLAPPED_BY,
    INTERVAL_OVERLAPPED_BY: INTERVAL_OVERLAPS,
    INTERVAL_STARTS: INTERVAL_STARTED_BY,
    INTERVAL_STARTED_BY: INTERVAL_STARTS,
    INTERVAL_DURING: INTERVAL_CONTAINS,
    INTERVAL_CONTAINS: INTERVAL_DURING,
    INTERVAL_FINISHES: INTERVAL_FINISHED_BY,
    INTERVAL_FINISHED_BY: INTERVAL_FINISHES,
    INTERVAL_EQUALS: INTERVAL_EQUALS,
}

ClosedInterval = tuple[date, date]


def calendar_day(value: datetime | date) -> date:
    """Normalize a timestamptz to its UTC day; preserve a calendar date."""
    if isinstance(value, datetime):
        if value.utcoffset() is not None:
            value = value.astimezone(timezone.utc)
        return value.date()
    return value


def interval_from_post(created_at: datetime | date) -> ClosedInterval:
    """Return the post's observed UTC creation day as a point interval."""
    start = calendar_day(created_at)
    return start, start


def allen_interval_relation(parent: ClosedInterval, child: ClosedInterval) -> str:
    """Return the Allen relation of ``parent`` toward ``child``.

    Both intervals are closed. The thirteen relations partition every
    pair of well-formed intervals (Allen, 1983).
    """
    parent_start, parent_end = parent
    child_start, child_end = child
    if parent_start > parent_end or child_start > child_end:
        raise ValueError(f"inverted interval: parent={parent} child={child}")
    if parent_start == child_start and parent_end == child_end:
        return INTERVAL_EQUALS
    if parent_end < child_start:
        return INTERVAL_BEFORE
    if child_end < parent_start:
        return INTERVAL_AFTER
    if parent_end == child_start:
        return INTERVAL_MEETS
    if child_end == parent_start:
        return INTERVAL_MET_BY
    if parent_start < child_start and parent_end < child_end and child_start < parent_end:
        return INTERVAL_OVERLAPS
    if child_start < parent_start and child_end < parent_end and parent_start < child_end:
        return INTERVAL_OVERLAPPED_BY
    if parent_start == child_start and parent_end < child_end:
        return INTERVAL_STARTS
    if parent_start == child_start and child_end < parent_end:
        return INTERVAL_STARTED_BY
    if child_start < parent_start and parent_end < child_end:
        return INTERVAL_DURING
    if parent_start < child_start and child_end < parent_end:
        return INTERVAL_CONTAINS
    if parent_end == child_end and parent_start > child_start:
        return INTERVAL_FINISHES
    if parent_end == child_end and parent_start < child_start:
        return INTERVAL_FINISHED_BY
    # The thirteen branches above exhaust every pair of valid closed intervals.
    raise ValueError(  # pragma: no cover - defensive invariant
        f"unclassified intervals parent={parent} child={child}"
    )


def interval_relation_from_current(code: str, current_is_parent: bool) -> str:
    """Orient a stored parent→child code toward the post the buyer opened.

    The edge stores the parent's relation toward the child. Opening the
    child must show the inverse (Contains → During) rather than claiming
    the child contains its parent. Unknown codes stay as stored -- this
    does not invent a thirteenth-plus relation.
    """
    if current_is_parent:
        return code
    return INTERVAL_RELATION_INVERSE.get(code, code)
