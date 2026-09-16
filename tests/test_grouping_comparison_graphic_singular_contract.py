"""Executable contract for persisted singular values on the comparison graphic."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PLOT_SOURCE = ROOT / "frontend" / "src" / "components" / "LeftoverMapPlot.tsx"
SINGULAR_SOURCE = ROOT / "frontend" / "src" / "leftoverMapPlotAxisSingular.ts"


def test_comparison_graphic_has_distinct_persisted_singular_value_copy() -> None:
    """Comparison-axis σ copy must remain distinct from report, strip, share, and tick copy."""
    assert SINGULAR_SOURCE.exists(), (
        "comparison graphic singular-value helper is missing; do not infer σ from axis share"
    )
    singular_source = SINGULAR_SOURCE.read_text(encoding="utf-8")
    plot_source = PLOT_SOURCE.read_text(encoding="utf-8")

    assert (
        'export const LEFTOVER_MAP_COMPARE_PLOT_AXIS_SINGULAR =\n'
        '  "leftover map comparison graphic leftover-map axis {axis} σ {value}";'
        in singular_source
    )
    assert (
        'export const LEFTOVER_MAP_COMPARE_PLOT_AXIS_SINGULAR_SHARE =\n'
        '  "leftover map comparison graphic leftover-map axis {axis} σ {value} ({share}%)";'
        in singular_source
    )
    assert "LEFTOVER_MAP_COMPARE_PLOT_AXIS_SINGULAR" in plot_source
    assert "LEFTOVER_MAP_COMPARE_PLOT_AXIS_SINGULAR_SHARE" in plot_source


def test_singular_value_is_read_from_axis_evidence_and_fails_closed() -> None:
    """Persisted σ and share are formatted independently; neither is derived from the other."""
    assert SINGULAR_SOURCE.exists(), "persisted singular-value projection helper is missing"
    singular_source = SINGULAR_SOURCE.read_text(encoding="utf-8")
    badge_source = singular_source.split(
        "export function leftoverMapComparePlotAxisBadge", 1
    )[-1].split("export function leftoverMapCompareAxisBadge", 1)[0]

    assert "axis.leftover_singular_value" in badge_source
    assert "axis.leftover_share" in badge_source
    assert "formatLeftoverMapPlotAxisSingular" in badge_source
    assert "formatLeftoverMapPlotAxisShare" in badge_source
    assert "Number.isFinite" in singular_source
    assert "< 0" in singular_source
    assert "return null" in singular_source
    assert ".toFixed(2)" in singular_source
    assert "Math.sqrt" not in badge_source
    assert "Math.max" not in badge_source
    assert "Math.min" not in badge_source
