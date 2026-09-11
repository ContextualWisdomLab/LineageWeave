"""Executable contract for persisted rank on the grouping-comparison graphic."""

from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]
PLOT_SOURCE = ROOT / "frontend" / "src" / "components" / "LeftoverMapPlot.tsx"
LAYOUT_SOURCE = ROOT / "frontend" / "src" / "leftoverMapPlotLayout.ts"
RANK_SOURCE = ROOT / "frontend" / "src" / "leftoverMapRank.ts"


def test_comparison_graphic_names_the_persisted_rank_with_distinct_copy() -> None:
    """Comparison SVG rank captions must not reuse report or strip accessible names."""
    plot_source = PLOT_SOURCE.read_text(encoding="utf-8")
    rank_source = RANK_SOURCE.read_text(encoding="utf-8")

    assert (
        'export const LEFTOVER_MAP_COMPARE_PLOT_SEGMENT_RANK =\n'
        '  "leftover map comparison graphic leftover-map rank {label}";'
        in rank_source
    )
    assert "LEFTOVER_MAP_COMPARE_PLOT_SEGMENT_RANK" in plot_source
    assert re.search(
        r'variant\s*===\s*"comparison"\s*\?\s*LEFTOVER_MAP_COMPARE_PLOT_SEGMENT_RANK\s*:\s*LEFTOVER_MAP_PLOT_SEGMENT_RANK',
        plot_source,
        re.DOTALL,
    )
    assert "label: segment.rankLabel" in plot_source


def test_rank_projection_consumes_only_persisted_fail_closed_evidence() -> None:
    """Rank zero stays explicit while missing, negative, and non-integer evidence omits."""
    layout_source = LAYOUT_SOURCE.read_text(encoding="utf-8")
    rank_source = RANK_SOURCE.read_text(encoding="utf-8")

    assert re.search(
        r"formatLeftoverMapRank\(\s*pair\.leftover_map_rank\s*\)",
        layout_source,
    )
    assert "rank == null || !Number.isInteger(rank) || rank < 0" in rank_source
    assert "return null;" in rank_source
    assert "return `rank ${rank}`;" in rank_source
    assert "Math.round" not in rank_source
    assert "Math.max" not in rank_source
    assert "Math.min" not in rank_source
    assert "Math.abs" not in rank_source
