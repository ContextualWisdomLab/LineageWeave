"""Executable contract for persisted distance on the grouping-comparison graphic."""

from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]
PLOT_SOURCE = ROOT / "frontend" / "src" / "components" / "LeftoverMapPlot.tsx"
LAYOUT_SOURCE = ROOT / "frontend" / "src" / "leftoverMapPlotLayout.ts"


def test_comparison_graphic_names_persisted_distance_with_distinct_localized_copy() -> None:
    """Comparison distance composes localized graphic and distance vocabulary."""
    plot_source = PLOT_SOURCE.read_text(encoding="utf-8")
    layout_source = LAYOUT_SOURCE.read_text(encoding="utf-8")

    assert "LEFTOVER_MAP_COMPARE_PLOT_SEGMENT_DISTANCE" not in layout_source
    assert "LEFTOVER_MAP_COMPARE_PLOT_SEGMENT_DISTANCE" not in plot_source
    assert 'variant === "comparison"' in plot_source
    assert (
        '`${t(LEFTOVER_MAP_COMPARE_PLOT_LABEL)}: ${tf(LEFTOVER_MAP_PLOT_SEGMENT_DISTANCE, {'
        in plot_source
    )
    assert "label: segment.distanceLabel" in plot_source
    assert ': tf(LEFTOVER_MAP_PLOT_SEGMENT_DISTANCE, { label: segment.distanceLabel })' in plot_source


def test_distance_projection_consumes_persisted_fail_closed_evidence() -> None:
    """Missing/non-finite distance omits while finite zero and signed values remain data-driven."""
    layout_source = LAYOUT_SOURCE.read_text(encoding="utf-8")

    assert re.search(
        r"formatLeftoverMapDistance\(\s*pair\.leftover_distance\s*\)",
        layout_source,
    )
    assert "value == null || !Number.isFinite(value)" in layout_source
    assert "return `d ${value.toFixed(2)}`;" in layout_source
    assert "Math.max(value" not in layout_source
    assert "Math.min(value" not in layout_source
    assert "Math.abs(value" not in layout_source
