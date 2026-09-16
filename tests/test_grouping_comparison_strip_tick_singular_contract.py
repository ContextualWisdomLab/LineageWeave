"""Executable contract for comparison-strip axis tick singular-value captions."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SINGULAR_SOURCE = ROOT / "frontend" / "src" / "leftoverMapPlotAxisSingular.ts"


def test_comparison_strip_axis_tick_keeps_persisted_singular_value_without_share() -> None:
    """A comparison-strip tick may name valid persisted σ even without axis share."""
    assert SINGULAR_SOURCE.exists(), "singular-value axis helper is missing"
    source = SINGULAR_SOURCE.read_text(encoding="utf-8")

    assert "leftoverMapCompareAxisTickBadge" in source
    assert "leftover map comparison leftover axis {axis} tick {value} σ {singular}" in source


def test_comparison_strip_axis_tick_does_not_infer_sigma_or_share() -> None:
    """Comparison-strip ticks compose persisted σ/share without deriving either field."""
    assert SINGULAR_SOURCE.exists(), "singular-value axis helper is missing"
    source = SINGULAR_SOURCE.read_text(encoding="utf-8")
    helper = source.split("export function leftoverMapCompareAxisTickBadge", 1)[-1]

    assert "formatLeftoverMapPlotAxisSingular" in helper
    assert "formatLeftoverMapPlotAxisShare" in helper
    assert "leftoverSingular" in helper
    assert "leftoverShare" in helper
    assert "LEFTOVER_MAP_COMPARE_AXIS_TICK_SHARE" in helper
    assert "LEFTOVER_MAP_COMPARE_AXIS_TICK_SINGULAR_SHARE" in helper
    assert "Math.sqrt" not in helper
    assert "Math.max" not in helper
    assert "Math.min" not in helper
