"""Executable contract for period/report leftover-axis tick singular captions."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BADGE_SOURCE = ROOT / "frontend" / "src" / "leftoverMapAxisBadge.ts"
BADGE_TEST_SOURCE = ROOT / "frontend" / "src" / "leftoverMapAxisBadge.test.ts"


def test_report_leftover_axis_tick_keeps_persisted_singular_without_share() -> None:
    """A report leftover-axis tick may name valid persisted σ with no axis share."""
    assert BADGE_SOURCE.exists(), "report-axis badge helper is missing"
    source = BADGE_SOURCE.read_text(encoding="utf-8")

    assert "leftoverMapAxisTickBadge" in source
    assert "leftover axis {axis} tick {value} σ {singular}" in source


def test_report_leftover_axis_tick_never_derives_sigma_or_share() -> None:
    """Tick composition delegates both persisted measures instead of synthesizing either one."""
    assert BADGE_SOURCE.exists(), "report-axis badge helper is missing"
    source = BADGE_SOURCE.read_text(encoding="utf-8")

    assert "formatLeftoverMapPlotAxisSingular(leftoverSingular)" in source
    assert "formatLeftoverMapPlotAxisShare(leftoverShare)" in source
    assert "Math.sqrt" not in source
    assert "Math.max" not in source


def test_report_leftover_axis_tick_behavior_preserves_zero_and_empty_state() -> None:
    """The executable frontend contract preserves finite zero and rejects unusable evidence."""
    assert BADGE_TEST_SOURCE.exists(), "report-axis badge behavior tests are missing"
    source = BADGE_TEST_SOURCE.read_text(encoding="utf-8")

    assert 'leftoverMapAxisTickBadge(1, "0.50", 0, null)' in source
    assert 'singular: "0.00"' in source
    assert 'leftoverMapAxisTickBadge(1, "0.00", Number.NaN, Number.POSITIVE_INFINITY)' in source
