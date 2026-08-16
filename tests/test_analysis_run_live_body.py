"""True write-clock comparison against an analysis-run knowledge cutoff.

A January 2026 run must not treat an August rewrite of an in-cutoff title
as reconstructed evidence. W3C Time / ISO 8601-1:2019 keep the analysis
clock and the live row write clock distinct (ADR 0016).
"""

from __future__ import annotations

from datetime import datetime, timezone

from lineageweave.analysis_run_live_body import live_body_written_after_cutoff


def test_rewritten_in_cutoff_title_is_not_reconstructed_evidence() -> None:
    """created_at can precede the cutoff while updated_at does not."""
    cutoff = datetime(2026, 1, 12, 12, 0, tzinfo=timezone.utc)
    created_at = datetime(2026, 1, 10, 12, 0, tzinfo=timezone.utc)
    rewritten_at = datetime(2026, 2, 1, 0, 0, tzinfo=timezone.utc)
    assert created_at <= cutoff
    assert live_body_written_after_cutoff(cutoff, rewritten_at) is True


def test_backdated_write_clock_stays_inside_the_cutoff() -> None:
    cutoff = datetime(2026, 1, 12, 12, 0, tzinfo=timezone.utc)
    updated_at = datetime(2026, 1, 10, 12, 0, tzinfo=timezone.utc)
    assert live_body_written_after_cutoff(cutoff, updated_at) is False


def test_write_clock_equal_to_cutoff_stays_inside() -> None:
    cutoff = datetime(2026, 1, 12, 12, 0, tzinfo=timezone.utc)
    assert live_body_written_after_cutoff(cutoff, cutoff) is False
