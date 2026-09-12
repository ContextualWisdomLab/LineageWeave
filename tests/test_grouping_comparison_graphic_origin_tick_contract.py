"""Executable contract for comparison-graphic origin tick captions."""

from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]
SINGULAR_SOURCE = ROOT / "frontend" / "src" / "leftoverMapPlotAxisSingular.ts"


def test_comparison_graphic_origin_tick_has_distinct_four_state_copy() -> None:
    """Origin ticks stay distinct across empty, share-only, singular-only, and combined evidence."""
    source = SINGULAR_SOURCE.read_text(encoding="utf-8")

    for text in (
        "leftover map comparison graphic leftover-map axis {axis} origin tick {value}",
        "leftover map comparison graphic leftover-map axis {axis} origin tick {value} {share}%",
        "leftover map comparison graphic leftover-map axis {axis} origin tick {value} σ {singular}",
        "leftover map comparison graphic leftover-map axis {axis} origin tick {value} σ {singular} {share}%",
    ):
        assert text in source
    assert "leftoverMapPlotTickIsOrigin" in source
    assert "leftoverMapComparePlotTickAxisBadge" in source


def test_origin_is_exact_formatted_zero_not_derived_from_share_or_singular() -> None:
    """Origin identity follows the canonical formatted zero tick and does not use evidence magnitude."""
    source = SINGULAR_SOURCE.read_text(encoding="utf-8")
    helper = re.search(
        r"export function leftoverMapPlotTickIsOrigin\(.*?\n}\n",
        source,
        re.DOTALL,
    )
    assert helper is not None
    helper_source = helper.group(0)

    assert "formatSignedLeftoverValue(0)" in helper_source
    assert "tickLabel === originLabel" in helper_source
    assert "leftover_share" not in helper_source
    assert "singular" not in helper_source.lower()
    assert "Math.abs" not in helper_source
