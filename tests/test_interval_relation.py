"""Allen interval relations are exhaustive and ticket windows stay honest."""

from __future__ import annotations

from datetime import date, datetime

import pytest

from lineageweave.fixtures import sample_records
from lineageweave.interval_relation import (
    INTERVAL_AFTER,
    INTERVAL_BEFORE,
    INTERVAL_CONTAINS,
    INTERVAL_DURING,
    INTERVAL_EQUALS,
    INTERVAL_FINISHED_BY,
    INTERVAL_FINISHES,
    INTERVAL_MEETS,
    INTERVAL_MET_BY,
    INTERVAL_OVERLAPPED_BY,
    INTERVAL_OVERLAPS,
    INTERVAL_STARTED_BY,
    INTERVAL_STARTS,
    allen_interval_relation,
    interval_from_post,
    interval_relation_from_current,
)
from lineageweave.lineage_persistence import lineage_edge_specs


def _d(month: int, day: int) -> date:
    return date(2026, month, day)


def test_all_thirteen_allen_relations_are_partitioned() -> None:
    cases = (
        ((_d(1, 1), _d(1, 2)), (_d(1, 4), _d(1, 5)), INTERVAL_BEFORE),
        ((_d(1, 4), _d(1, 5)), (_d(1, 1), _d(1, 2)), INTERVAL_AFTER),
        ((_d(1, 1), _d(1, 3)), (_d(1, 3), _d(1, 5)), INTERVAL_MEETS),
        ((_d(1, 3), _d(1, 5)), (_d(1, 1), _d(1, 3)), INTERVAL_MET_BY),
        ((_d(1, 1), _d(1, 4)), (_d(1, 3), _d(1, 6)), INTERVAL_OVERLAPS),
        ((_d(1, 3), _d(1, 6)), (_d(1, 1), _d(1, 4)), INTERVAL_OVERLAPPED_BY),
        ((_d(1, 1), _d(1, 2)), (_d(1, 1), _d(1, 5)), INTERVAL_STARTS),
        ((_d(1, 1), _d(1, 5)), (_d(1, 1), _d(1, 2)), INTERVAL_STARTED_BY),
        ((_d(1, 3), _d(1, 4)), (_d(1, 1), _d(1, 6)), INTERVAL_DURING),
        ((_d(1, 1), _d(1, 6)), (_d(1, 3), _d(1, 4)), INTERVAL_CONTAINS),
        ((_d(1, 3), _d(1, 6)), (_d(1, 1), _d(1, 6)), INTERVAL_FINISHES),
        ((_d(1, 1), _d(1, 6)), (_d(1, 3), _d(1, 6)), INTERVAL_FINISHED_BY),
        ((_d(1, 2), _d(1, 4)), (_d(1, 2), _d(1, 4)), INTERVAL_EQUALS),
    )
    for parent, child, expected in cases:
        assert allen_interval_relation(parent, child) == expected


def test_point_intervals_on_different_days_are_before_not_meets() -> None:
    assert (
        allen_interval_relation((_d(1, 5), _d(1, 5)), (_d(1, 6), _d(1, 6)))
        == INTERVAL_BEFORE
    )


def test_missing_due_date_is_a_point_interval() -> None:
    assert interval_from_post(datetime(2026, 1, 6, 15, 0, 0), None) == (
        _d(1, 6),
        _d(1, 6),
    )


def test_earlier_due_date_is_not_inverted() -> None:
    assert interval_from_post(_d(1, 10), _d(1, 6)) == (_d(1, 10), _d(1, 10))


def test_inverted_bounds_fail_closed() -> None:
    with pytest.raises(ValueError, match="inverted"):
        allen_interval_relation((_d(1, 5), _d(1, 1)), (_d(1, 6), _d(1, 7)))


def test_a100_ticket_windows_contain_and_overlap_the_designed_fork() -> None:
    """Seed tickets make rec-002 contain rec-003 and overlap rec-004.

    Pricing follow-up is 2026-01-06 with due 2026-01-12. Revised quote
    is a point on 2026-01-10. Delivery question is 2026-01-07 through
    2026-01-16. Reconstruct still owns the parent choice; this only
    names the Allen relation on those edges.
    """
    records = {record.record_id: record for record in sample_records()}
    dues = {
        "rec-002": date(2026, 1, 12),
        "rec-004": date(2026, 1, 16),
        "rec-102": date(2026, 1, 14),
    }
    edges = lineage_edge_specs(sample_records())
    relations = {
        (edge.parent_id, edge.child_id): allen_interval_relation(
            interval_from_post(records[edge.parent_id].occurred_at, dues.get(edge.parent_id)),
            interval_from_post(records[edge.child_id].occurred_at, dues.get(edge.child_id)),
        )
        for edge in edges
    }
    assert relations[("rec-001", "rec-002")] == INTERVAL_BEFORE
    assert relations[("rec-002", "rec-003")] == INTERVAL_CONTAINS
    assert relations[("rec-002", "rec-004")] == INTERVAL_OVERLAPS
    assert (
        interval_relation_from_current(relations[("rec-002", "rec-003")], False)
        == INTERVAL_DURING
    )
    assert (
        interval_relation_from_current(relations[("rec-002", "rec-004")], False)
        == INTERVAL_OVERLAPPED_BY
    )


def test_inverse_is_involution_for_all_thirteen_relations() -> None:
    from lineageweave.interval_relation import INTERVAL_RELATION_CODES

    for code in INTERVAL_RELATION_CODES:
        flipped = interval_relation_from_current(code, False)
        assert interval_relation_from_current(flipped, False) == code
        assert interval_relation_from_current(code, True) == code
