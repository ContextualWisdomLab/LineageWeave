"""Executable contract for persisted singular values on report-graphic axes."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SINGULAR_SOURCE = ROOT / "frontend" / "src" / "leftoverMapPlotAxisSingular.ts"
PLOT_SOURCE = ROOT / "frontend" / "src" / "components" / "LeftoverMapPlot.tsx"


def test_report_graphic_axis_has_distinct_singular_and_singular_share_copy() -> None:
    """Report-graphic σ copy must stay distinct from pair badges and comparison variants."""
    assert SINGULAR_SOURCE.exists(), "persisted singular-value projection helper is missing"
    source = SINGULAR_SOURCE.read_text(encoding="utf-8")
    plot_source = PLOT_SOURCE.read_text(encoding="utf-8")

    assert 'LEFTOVER_MAP_PLOT_AXIS_SINGULAR = "leftover-map axis {axis} σ {value}"' in source
    assert (
        'LEFTOVER_MAP_PLOT_AXIS_SINGULAR_SHARE =\n'
        '  "leftover-map axis {axis} σ {value} ({share}%)"'
        in source
    )
    assert "LEFTOVER_MAP_PLOT_AXIS_SINGULAR" in plot_source
    assert "LEFTOVER_MAP_PLOT_AXIS_SINGULAR_SHARE" in plot_source


def test_report_graphic_singular_value_comes_from_persisted_axis_evidence() -> None:
    """Invalid σ omits independently of share; finite σ=0 remains explicit."""
    assert SINGULAR_SOURCE.exists(), "persisted singular-value projection helper is missing"
    source = SINGULAR_SOURCE.read_text(encoding="utf-8")

    assert "leftover_singular_value" in source
    assert "Number.isFinite" in source
    assert "< 0" in source
    assert ".toFixed(2)" in source
    assert "Math.sqrt" not in source
    assert "Math.max" not in source
