"""Executable contract for the report-axis singular-only state."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BADGE_SOURCE = ROOT / "frontend" / "src" / "leftoverMapAxisBadge.ts"


def test_report_axis_badge_preserves_singular_when_share_is_missing() -> None:
    """A valid persisted σ remains visible when axis share is absent."""
    assert BADGE_SOURCE.exists(), "report-axis singular-value badge helper is missing"
    source = BADGE_SOURCE.read_text(encoding="utf-8")

    assert (
        'LEFTOVER_MAP_AXIS_BADGE_SINGULAR_ONLY = "leftover axis {axis} σ {value}"'
        in source
    )
    assert "leftoverMapAxisBadge(" in source
    assert "LEFTOVER_MAP_AXIS_BADGE_SINGULAR_ONLY" in source


def test_report_axis_badge_keeps_sigma_and_share_missingness_independent() -> None:
    """σ-only, share-only, combined, and empty states must remain data-driven."""
    assert BADGE_SOURCE.exists(), "report-axis singular-value badge helper is missing"
    source = BADGE_SOURCE.read_text(encoding="utf-8")

    assert "formatLeftoverMapPlotAxisSingular" in source
    assert "leftoverMapAxisBadgeShare" in source
    assert "LEFTOVER_MAP_AXIS_BADGE_SINGULAR" in source
    assert "LEFTOVER_MAP_AXIS_BADGE_SHARE" in source
    assert "LEFTOVER_MAP_AXIS_BADGE_SINGULAR_ONLY" in source
    assert "Math.sqrt" not in source
