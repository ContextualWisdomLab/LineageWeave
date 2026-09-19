"""Executable contract for persisted singular values on the comparison graphic."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PLOT_SOURCE = ROOT / "frontend" / "src" / "components" / "LeftoverMapPlot.tsx"
SINGULAR_SOURCE = ROOT / "frontend" / "src" / "leftoverMapPlotAxisSingular.ts"


def _exported_function_source(source: str, signature: str) -> str:
    """Return one exported function so independence checks do not police sibling composition."""
    start = source.index(signature)
    next_export = source.find("\nexport function ", start + len(signature))
    if next_export == -1:
        return source[start:]
    return source[start:next_export]


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
    """Persisted σ=0 stays explicit; missing, non-finite, or negative σ omits independently."""
    assert SINGULAR_SOURCE.exists(), "persisted singular-value projection helper is missing"
    singular_source = SINGULAR_SOURCE.read_text(encoding="utf-8")
    formatter_source = _exported_function_source(
        singular_source,
        "export function formatLeftoverMapPlotAxisSingular",
    )

    assert "Number.isFinite" in formatter_source
    assert "< 0" in formatter_source
    assert "return null" in formatter_source
    assert ".toFixed(2)" in formatter_source
    assert "leftover_share" not in formatter_source
    assert "Math.sqrt" not in formatter_source
    assert "Math.max" not in formatter_source
    assert "Math.min" not in formatter_source

    # Comparison composition may display independently persisted σ and share together;
    # it must delegate to each evidence formatter instead of deriving one from the other.
    assert (
        "const singular = formatLeftoverMapPlotAxisSingular(axis.leftover_singular_value);"
        in singular_source
    )
    assert "const share = formatLeftoverMapPlotAxisShare(axis.leftover_share);" in singular_source
