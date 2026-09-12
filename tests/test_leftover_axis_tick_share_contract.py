"""Executable contract for report leftover-axis tick share captions."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BADGE_SOURCE = ROOT / "frontend" / "src" / "leftoverMapAxisBadge.ts"


def test_report_axis_tick_keeps_axis_share_independent_of_singular() -> None:
    """A report leftover-axis tick may name persisted share when singular evidence is absent."""
    assert BADGE_SOURCE.exists(), "report-axis badge helper is missing"
    source = BADGE_SOURCE.read_text(encoding="utf-8")

    assert "leftoverMapAxisTickBadge" in source
    assert "leftover axis {axis} tick {value} {share}%" in source
    assert "leftover axis {axis} tick {value} σ {singular} {share}%" in source


def test_report_axis_tick_never_infers_share_from_singular() -> None:
    """Share-only, singular-only, combined, and empty states remain persisted-data decisions."""
    assert BADGE_SOURCE.exists(), "report-axis badge helper is missing"
    source = BADGE_SOURCE.read_text(encoding="utf-8")

    assert "Number.isFinite" in source
    assert "leftover_share" in source
    assert "formatLeftoverMapPlotAxisSingular" in source
    assert "Math.sqrt" not in source
    assert "Math.max" not in source
