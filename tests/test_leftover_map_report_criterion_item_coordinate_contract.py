"""Executable contract for report-graphic criterion item-coordinate captions."""

from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]
LAYOUT_SOURCE = ROOT / "frontend" / "src" / "leftoverMapPlotLayout.ts"
PLOT_SOURCE = ROOT / "frontend" / "src" / "components" / "LeftoverMapPlot.tsx"


def test_report_graphic_criterion_names_persisted_item_coordinates() -> None:
    """Report criterion markers use distinct ζ copy while comparison markers retain generic copy."""
    layout_source = LAYOUT_SOURCE.read_text(encoding="utf-8")
    plot_source = PLOT_SOURCE.read_text(encoding="utf-8")

    assert 'LEFTOVER_MAP_PLOT_CRITERION =\n  "leftover-map criterion {label} at ζ {item}";' in layout_source
    assert "leftoverMapPlotCriterionBadge" in layout_source
    assert "leftoverMapPlotCriterionBadge" in plot_source
    assert re.search(
        r'variant\s*===\s*"comparison".*?Criterion ζ.*?leftoverMapPlotCriterionBadge',
        plot_source,
        re.DOTALL,
    )


def test_criterion_badge_consumes_item_axes_fail_closed_without_person_inference() -> None:
    """ζ comes only from a finite persisted item coordinate pair; zero remains representable."""
    layout_source = LAYOUT_SOURCE.read_text(encoding="utf-8")
    helper = re.search(
        r"export function leftoverMapPlotCriterionBadge\(.*?\n}\n",
        layout_source,
        re.DOTALL,
    )
    assert helper is not None
    helper_source = helper.group(0)

    assert "formatLeftoverMapCoordinatePair(axis1, axis2)" in helper_source
    assert "item === null" in helper_source
    assert "return null" in helper_source
    assert "leftover_map_person_axis" not in helper_source
    assert "Math.sqrt" not in helper_source
    assert "Math.abs" not in helper_source
