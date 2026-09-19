"""Executable contract for comparison-strip axis tick share captions."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SINGULAR_SOURCE = ROOT / "frontend" / "src" / "leftoverMapPlotAxisSingular.ts"


def test_comparison_strip_tick_keeps_axis_share_independent_of_singular() -> None:
    """A comparison-strip tick may name persisted share when singular evidence is absent."""
    assert SINGULAR_SOURCE.exists(), "comparison-strip axis projection helper is missing"
    source = SINGULAR_SOURCE.read_text(encoding="utf-8")

    assert "leftoverMapCompareAxisTickBadge" in source
    assert "leftover map comparison leftover axis {axis} tick {value} {share}%" in source
    assert "leftover map comparison leftover axis {axis} tick {value} σ {singular} {share}%" in source


def test_comparison_strip_tick_never_infers_share_from_singular() -> None:
    """Share-only, singular-only, combined, and empty states remain persisted-data decisions."""
    assert SINGULAR_SOURCE.exists(), "comparison-strip axis projection helper is missing"
    source = SINGULAR_SOURCE.read_text(encoding="utf-8")

    assert "Number.isFinite" in source
    assert "leftover_share" in source
    assert "formatLeftoverMapPlotAxisSingular" in source
    assert "Math.sqrt" not in source
    assert "Math.max" not in source
