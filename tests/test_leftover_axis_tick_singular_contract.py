"""Executable contract for period/report leftover-axis tick singular captions."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BADGE_SOURCE = ROOT / "frontend" / "src" / "leftoverMapAxisBadge.ts"
BADGE_TEST_SOURCE = ROOT / "frontend" / "src" / "leftoverMapAxisTickBadge.test.ts"


def test_report_leftover_axis_tick_keeps_persisted_singular_without_share() -> None:
    """A report leftover-axis tick may name valid persisted σ with no axis share."""
    assert BADGE_SOURCE.exists(), "report-axis badge helper is missing"
    source = BADGE_SOURCE.read_text(encoding="utf-8")

    assert "leftoverMapAxisTickBadge" in source
    assert "leftover axis {axis} tick {value} σ {singular}" in source


def test_report_leftover_axis_tick_never_infers_sigma_or_share() -> None:
    """Tick σ/share are delegated to their persisted-value formatters without derivation."""
    assert BADGE_SOURCE.exists(), "report-axis badge helper is missing"
    source = BADGE_SOURCE.read_text(encoding="utf-8")
    tick_badge = source.split("export function leftoverMapAxisTickBadge", 1)[1]

    assert "formatLeftoverMapPlotAxisSingular(leftoverSingular)" in tick_badge
    assert "formatLeftoverMapPlotAxisShare(leftoverShare)" in tick_badge
    assert "Math.sqrt(" not in tick_badge
    assert "Math.max(" not in tick_badge


def test_report_leftover_axis_tick_singular_states_are_executable() -> None:
    """Frontend tests execute singular-only zero and fail-closed invalid evidence states."""
    assert BADGE_TEST_SOURCE.exists(), "report-axis tick badge behavior test is missing"
    test_source = BADGE_TEST_SOURCE.read_text(encoding="utf-8")

    assert 'leftoverMapAxisTickBadge(1, "0.00", 0, null)' in test_source
    assert 'singular: "0.00"' in test_source
    assert "Number.NaN" in test_source
