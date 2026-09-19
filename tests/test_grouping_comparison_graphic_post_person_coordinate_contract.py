"""Executable contract for comparison-graphic post person-coordinate captions."""

from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]
LAYOUT_SOURCE = ROOT / "frontend" / "src" / "leftoverMapPlotLayout.ts"
PLOT_SOURCE = ROOT / "frontend" / "src" / "components" / "LeftoverMapPlot.tsx"


def test_comparison_graphic_post_names_persisted_person_coordinates() -> None:
    """Comparison post markers use distinct ξ copy without changing report markers."""
    layout_source = LAYOUT_SOURCE.read_text(encoding="utf-8")
    plot_source = PLOT_SOURCE.read_text(encoding="utf-8")

    assert (
        'LEFTOVER_MAP_COMPARE_PLOT_POST_ACTION =\n'
        '  "Open leftover map comparison graphic leftover-map post {title} at ξ {person}";'
        in layout_source
    )
    assert "leftoverMapComparePlotPostBadge" in layout_source
    assert "leftoverMapComparePlotPostBadge" in plot_source
    assert "LEFTOVER_MAP_PLOT_POST_ACTION" in plot_source
    assert re.search(
        r'variant\s*===\s*"comparison".*?leftoverMapComparePlotPostBadge.*?LEFTOVER_MAP_PLOT_POST_ACTION',
        plot_source,
        re.DOTALL,
    )


def test_comparison_post_badge_consumes_person_axes_fail_closed_without_item_inference() -> None:
    """Comparison ξ comes only from finite persisted person axes; zero remains explicit."""
    layout_source = LAYOUT_SOURCE.read_text(encoding="utf-8")
    helper = re.search(
        r"export function leftoverMapComparePlotPostBadge\(.*?\n}\n",
        layout_source,
        re.DOTALL,
    )
    assert helper is not None
    helper_source = helper.group(0)

    assert "formatLeftoverMapCoordinatePair(axis1, axis2)" in helper_source
    assert "person === null" in helper_source
    assert "return null" in helper_source
    assert "LEFTOVER_MAP_COMPARE_PLOT_POST_ACTION" in helper_source
    assert "leftover_map_item_axis" not in helper_source
    assert "Math.sqrt" not in helper_source
    assert "Math.abs" not in helper_source
