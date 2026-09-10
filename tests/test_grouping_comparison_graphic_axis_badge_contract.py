"""Executable contract for comparison-graphic axis singular/share composition."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SINGULAR_SOURCE = ROOT / "frontend" / "src" / "leftoverMapPlotAxisSingular.ts"


def test_comparison_graphic_axis_badge_preserves_singular_when_share_is_missing() -> None:
    """Valid persisted σ remains visible on the comparison graphic without share."""
    assert SINGULAR_SOURCE.exists(), "comparison singular-value helper is missing"
    source = SINGULAR_SOURCE.read_text(encoding="utf-8")

    assert "leftoverMapComparePlotAxisBadge" in source
    assert (
        'LEFTOVER_MAP_COMPARE_PLOT_AXIS_SINGULAR =\n'
        '  "leftover map comparison graphic leftover-map axis {axis} σ {value}"'
        in source
    )
    assert "LEFTOVER_MAP_COMPARE_PLOT_AXIS_SINGULAR_SHARE" in source
    assert "LEFTOVER_MAP_COMPARE_PLOT_AXIS_SHARE" in source


def test_comparison_graphic_axis_badge_keeps_sigma_and_share_independent() -> None:
    """σ-only, share-only, combined, and empty states remain persisted-data decisions."""
    assert SINGULAR_SOURCE.exists(), "comparison singular-value helper is missing"
    source = SINGULAR_SOURCE.read_text(encoding="utf-8")

    assert "formatLeftoverMapPlotAxisSingular" in source
    assert "Number.isFinite" in source
    assert "Math.sqrt" not in source
    assert "Math.max" not in source
