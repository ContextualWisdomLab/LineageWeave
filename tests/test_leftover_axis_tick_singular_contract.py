"""Executable contract for period/report leftover-axis tick singular captions."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BADGE_SOURCE = ROOT / "frontend" / "src" / "leftoverMapAxisBadge.ts"


def test_report_leftover_axis_tick_keeps_persisted_singular_without_share() -> None:
    """A report leftover-axis tick may name valid persisted σ with no axis share."""
    assert BADGE_SOURCE.exists(), "report-axis badge helper is missing"
    source = BADGE_SOURCE.read_text(encoding="utf-8")

    assert "leftoverMapAxisTickBadge" in source
    assert "leftover axis {axis} tick {value} σ {singular}" in source


def test_report_leftover_axis_tick_never_infers_sigma_or_share() -> None:
    """Invalid σ falls back to an ordinary leftover-axis tick; share is never synthesized."""
    assert BADGE_SOURCE.exists(), "report-axis badge helper is missing"
    source = BADGE_SOURCE.read_text(encoding="utf-8")

    assert "formatLeftoverMapPlotAxisSingular" in source
    assert "Math.sqrt" not in source
    tail = source.split("leftoverMapAxisTickBadge", 1)[-1][:1600]
    assert "leftover_share" not in tail
