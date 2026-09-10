"""Executable contract for comparison-strip leftover-axis singular badges."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SINGULAR_SOURCE = ROOT / "frontend" / "src" / "leftoverMapPlotAxisSingular.ts"


def test_comparison_strip_axis_badge_has_distinct_copy_for_share_and_singular() -> None:
    """Comparison-strip badge copy must be distinct from report and comparison-graphic axes."""
    assert SINGULAR_SOURCE.exists(), "comparison singular-value helper is missing"
    source = SINGULAR_SOURCE.read_text(encoding="utf-8")

    assert (
        'LEFTOVER_MAP_COMPARE_AXIS_SINGULAR =\n'
        '  "leftover map comparison leftover axis {axis} σ {value}"'
        in source
    )
    assert (
        'LEFTOVER_MAP_COMPARE_AXIS_SINGULAR_SHARE =\n'
        '  "leftover map comparison leftover axis {axis} σ {value} {share}%"'
        in source
    )
    assert (
        'LEFTOVER_MAP_COMPARE_AXIS_SHARE =\n'
        '  "leftover map comparison leftover axis {axis} {share}%"'
        in source
    )
    assert "leftoverMapCompareAxisBadge" in source


def test_comparison_strip_axis_badge_preserves_independent_missingness() -> None:
    """Share-only and σ-only states must not synthesize the missing counterpart."""
    assert SINGULAR_SOURCE.exists(), "comparison singular-value helper is missing"
    source = SINGULAR_SOURCE.read_text(encoding="utf-8")

    assert "formatLeftoverMapPlotAxisSingular" in source
    assert "Number.isFinite" in source
    assert "LEFTOVER_MAP_COMPARE_AXIS_SINGULAR_SHARE" in source
    assert "LEFTOVER_MAP_COMPARE_AXIS_SINGULAR" in source
    assert "LEFTOVER_MAP_COMPARE_AXIS_SHARE" in source
    assert "Math.sqrt" not in source
