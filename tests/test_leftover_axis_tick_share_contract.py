"""Executable contract for report leftover-axis tick share captions."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BADGE_SOURCE = ROOT / "frontend" / "src" / "leftoverMapAxisBadge.ts"
BADGE_TEST_SOURCE = ROOT / "frontend" / "src" / "leftoverMapAxisBadge.test.ts"


def test_report_axis_tick_keeps_axis_share_independent_of_singular() -> None:
    """A report leftover-axis tick may name persisted share when singular evidence is absent."""
    assert BADGE_SOURCE.exists(), "report-axis badge helper is missing"
    source = BADGE_SOURCE.read_text(encoding="utf-8")

    assert "leftoverMapAxisTickBadge" in source
    assert "leftover axis {axis} tick {value} {share}%" in source
    assert "leftover axis {axis} tick {value} σ {singular} {share}%" in source


def test_report_axis_tick_never_derives_share_from_singular() -> None:
    """Tick composition delegates validation and never derives persisted share from σ."""
    assert BADGE_SOURCE.exists(), "report-axis badge helper is missing"
    source = BADGE_SOURCE.read_text(encoding="utf-8")

    assert "formatLeftoverMapPlotAxisShare(leftoverShare)" in source
    assert "formatLeftoverMapPlotAxisSingular(leftoverSingular)" in source
    assert "Math.sqrt" not in source
    assert "Math.max" not in source


def test_report_axis_tick_behavior_covers_independent_persisted_states() -> None:
    """The executable frontend contract covers combined, share-only, and invalid evidence."""
    assert BADGE_TEST_SOURCE.exists(), "report-axis badge behavior tests are missing"
    source = BADGE_TEST_SOURCE.read_text(encoding="utf-8")

    assert 'describe("leftoverMapAxisTickBadge"' in source
    assert 'leftoverMapAxisTickBadge(1, "-0.50", 1.24, 0.42)' in source
    assert 'leftoverMapAxisTickBadge(2, "0.00", null, 0.18)' in source
    assert "Number.POSITIVE_INFINITY" in source
