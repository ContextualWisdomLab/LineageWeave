"""Executable contract for report-graphic tick singular-value captions."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SINGULAR_SOURCE = ROOT / "frontend" / "src" / "leftoverMapPlotAxisSingular.ts"
PLOT_COMPONENT_SOURCE = ROOT / "frontend" / "src" / "components" / "LeftoverMapPlot.tsx"


def test_report_graphic_tick_keeps_persisted_singular_value_without_share() -> None:
    """A tick may name valid persisted σ even when axis share is absent."""
    assert SINGULAR_SOURCE.exists(), "singular-value axis helper is missing"
    source = SINGULAR_SOURCE.read_text(encoding="utf-8")

    assert "leftoverMapPlotTickAxisBadge" in source
    assert "leftover-map axis {axis} tick {value} σ {singular}" in source


def test_report_graphic_consumes_tick_singular_projection() -> None:
    """The buyer-visible report graphic consumes independently persisted σ/share."""
    source = PLOT_COMPONENT_SOURCE.read_text(encoding="utf-8")

    assert "leftoverMapPlotTickAxisBadge" in source
    assert "leftoverSingularForAxis(leftoverMapAxes, tick.axis)" in source
    assert "leftoverShareForAxis(leftoverMapAxes, tick.axis)" in source
    assert "tf(reportTickBadge.template, reportTickBadge.values)" in source


def test_report_graphic_tick_does_not_infer_sigma_or_share() -> None:
    """Report ticks compose independently persisted σ/share without deriving either."""
    assert SINGULAR_SOURCE.exists(), "singular-value axis helper is missing"
    source = SINGULAR_SOURCE.read_text(encoding="utf-8")
    helper = source.split("export function leftoverMapPlotTickAxisBadge", 1)[-1].split(
        "export function leftoverMapComparePlotTickAxisBadge", 1
    )[0]

    assert "formatLeftoverMapPlotAxisSingular" in helper
    assert "formatLeftoverMapPlotAxisShare" in helper
    assert "leftoverSingular" in helper
    assert "leftoverShare" in helper
    assert "LEFTOVER_MAP_PLOT_TICK_SHARE" in helper
    assert "LEFTOVER_MAP_PLOT_TICK_SINGULAR_SHARE" in helper
    assert "Math.sqrt" not in helper
    assert "Math.max" not in helper
    assert "Math.min" not in helper
