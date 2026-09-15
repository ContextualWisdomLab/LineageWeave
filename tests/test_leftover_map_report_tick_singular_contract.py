"""Executable contract for report-graphic tick singular-value captions."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SINGULAR_SOURCE = ROOT / "frontend" / "src" / "leftoverMapPlotAxisSingular.ts"


def test_report_graphic_tick_keeps_persisted_singular_value_without_share() -> None:
    """A tick may name valid persisted σ even when axis share is absent."""
    assert SINGULAR_SOURCE.exists(), "singular-value axis helper is missing"
    source = SINGULAR_SOURCE.read_text(encoding="utf-8")

    assert "leftoverMapPlotTickAxisBadge" in source
    assert "leftover-map axis {axis} tick {value} σ {singular}" in source


def test_report_graphic_tick_does_not_infer_sigma_or_share() -> None:
    """Invalid σ falls back to the ordinary tick and ticks never synthesize share."""
    assert SINGULAR_SOURCE.exists(), "singular-value axis helper is missing"
    source = SINGULAR_SOURCE.read_text(encoding="utf-8")

    assert "formatLeftoverMapPlotAxisSingular" in source
    assert "Number.isFinite" in source
    assert "Math.sqrt" not in source
    assert "leftover_share" not in source.split("leftoverMapPlotTickAxisBadge", 1)[-1][:1400]
