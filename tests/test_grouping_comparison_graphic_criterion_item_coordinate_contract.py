"""Executable contract for comparison-graphic criterion item-coordinate captions."""

from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]
LAYOUT_SOURCE = ROOT / "frontend" / "src" / "leftoverMapPlotLayout.ts"
PLOT_SOURCE = ROOT / "frontend" / "src" / "components" / "LeftoverMapPlot.tsx"


def test_comparison_graphic_criterion_names_persisted_item_coordinates() -> None:
    """Comparison criterion markers use distinct ζ copy without changing report markers."""
    layout_source = LAYOUT_SOURCE.read_text(encoding="utf-8")
    plot_source = PLOT_SOURCE.read_text(encoding="utf-8")

    assert (
        'LEFTOVER_MAP_COMPARE_PLOT_CRITERION =\n'
        '  "leftover map comparison graphic leftover-map criterion {label} at ζ {item}";'
        in layout_source
    )
    assert "leftoverMapComparePlotCriterionBadge" in layout_source
    assert "leftoverMapComparePlotCriterionBadge" in plot_source
    assert "leftoverMapPlotCriterionBadge" in plot_source
    assert re.search(
        r'variant\s*===\s*"comparison".*?leftoverMapComparePlotCriterionBadge.*?leftoverMapPlotCriterionBadge',
        plot_source,
        re.DOTALL,
    )


def test_comparison_criterion_badge_consumes_item_axes_fail_closed_without_person_inference() -> None:
    """Comparison ζ comes only from finite persisted item axes; zero remains explicit."""
    layout_source = LAYOUT_SOURCE.read_text(encoding="utf-8")
    helper = re.search(
        r"export function leftoverMapComparePlotCriterionBadge\(.*?\n}\n",
        layout_source,
        re.DOTALL,
    )
    assert helper is not None
    helper_source = helper.group(0)

    assert "formatLeftoverMapCoordinatePair(axis1, axis2)" in helper_source
    assert "item === null" in helper_source
    assert "return null" in helper_source
    assert "LEFTOVER_MAP_COMPARE_PLOT_CRITERION" in helper_source
    assert "leftover_map_person_axis" not in helper_source
    assert "Math.sqrt" not in helper_source
    assert "Math.abs" not in helper_source
