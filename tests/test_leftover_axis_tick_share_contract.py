"""Executable contract for report leftover-axis tick share captions."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BADGE_SOURCE = ROOT / "frontend" / "src" / "leftoverMapAxisBadge.ts"
BADGE_TEST_SOURCE = ROOT / "frontend" / "src" / "leftoverMapAxisTickBadge.test.ts"


def test_report_axis_tick_keeps_axis_share_independent_of_singular() -> None:
    """A report leftover-axis tick may name persisted share when singular evidence is absent."""
    assert BADGE_SOURCE.exists(), "report-axis badge helper is missing"
    source = BADGE_SOURCE.read_text(encoding="utf-8")

    assert "leftoverMapAxisTickBadge" in source
    assert "leftover axis {axis} tick {value} {share}%" in source
    assert "leftover axis {axis} tick {value} σ {singular} {share}%" in source


def test_report_axis_tick_never_infers_share_from_singular() -> None:
    """Share is formatted from its persisted field rather than inferred from σ."""
    assert BADGE_SOURCE.exists(), "report-axis badge helper is missing"
    source = BADGE_SOURCE.read_text(encoding="utf-8")
    tick_badge = source.split("export function leftoverMapAxisTickBadge", 1)[1]

    assert "formatLeftoverMapPlotAxisShare(leftoverShare)" in tick_badge
    assert "formatLeftoverMapPlotAxisSingular(leftoverSingular)" in tick_badge
    assert "Math.sqrt(" not in tick_badge
    assert "Math.max(" not in tick_badge


def test_report_axis_tick_share_states_are_executable() -> None:
    """Frontend tests execute combined, share-only, and invalid persisted-share states."""
    assert BADGE_TEST_SOURCE.exists(), "report-axis tick badge behavior test is missing"
    test_source = BADGE_TEST_SOURCE.read_text(encoding="utf-8")

    assert 'leftoverMapAxisTickBadge(1, "0.25", 0.5, 0.4)' in test_source
    assert 'leftoverMapAxisTickBadge(2, "−0.25", null, 0.4)' in test_source
    assert "Number.POSITIVE_INFINITY" in test_source
