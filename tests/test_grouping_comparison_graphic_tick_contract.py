"""Executable wiring contract for coordinate ticks on the grouping-comparison graphic."""

from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]
PLOT_SOURCE = ROOT / "frontend" / "src" / "components" / "LeftoverMapPlot.tsx"
LAYOUT_SOURCE = ROOT / "frontend" / "src" / "leftoverMapPlotLayout.ts"
SINGULAR_SOURCE = ROOT / "frontend" / "src" / "leftoverMapPlotAxisSingular.ts"


def test_comparison_graphic_names_ticks_through_evidence_aware_badge_contract() -> None:
    """Comparison ticks consume persisted σ/share evidence and preserve distinct origin copy."""
    plot_source = PLOT_SOURCE.read_text(encoding="utf-8")
    singular_source = SINGULAR_SOURCE.read_text(encoding="utf-8")

    assert "leftoverMapComparePlotTickAxisBadge" in plot_source
    assert "leftoverSingularForAxis(leftoverMapAxes, tick.axis)" in plot_source
    assert "leftoverShareForAxis(leftoverMapAxes, tick.axis)" in plot_source
    assert "tf(comparisonTickBadge.template, comparisonTickBadge.values)" in plot_source
    assert (
        'export const LEFTOVER_MAP_COMPARE_PLOT_TICK =\n'
        '  "leftover map comparison graphic leftover-map axis {axis} tick {value}";'
        in singular_source
    )
    assert "LEFTOVER_MAP_COMPARE_PLOT_ORIGIN_TICK" in singular_source
    assert "LEFTOVER_MAP_COMPARE_PLOT_TICK_SINGULAR_SHARE" in singular_source


def test_tick_positions_come_from_persisted_coordinates_not_distance() -> None:
    """Tick candidates remain the origin plus finite persisted ξ/ζ projections."""
    layout_source = LAYOUT_SOURCE.read_text(encoding="utf-8")

    assert "const axis1Values = [0];" in layout_source
    assert "const axis2Values = [0];" in layout_source
    assert "pair.leftover_map_person_axis_1 as number" in layout_source
    assert "pair.leftover_map_item_axis_1 as number" in layout_source
    assert "pair.leftover_map_person_axis_2 as number" in layout_source
    assert "pair.leftover_map_item_axis_2 as number" in layout_source
    tick_builder = re.search(
        r"function uniqueCoordinateTicks\(.*?\n}\n",
        layout_source,
        re.DOTALL,
    )
    assert tick_builder is not None
    assert "leftover_distance" not in tick_builder.group(0)
