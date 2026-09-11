"""Executable contract for report-graphic tick axis-share captions."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SINGULAR_SOURCE = ROOT / "frontend" / "src" / "leftoverMapPlotAxisSingular.ts"


def test_report_graphic_tick_keeps_axis_share_independent_of_singular() -> None:
    """A report-graphic tick may name persisted share when singular evidence is absent."""
    assert SINGULAR_SOURCE.exists(), "report graphic axis projection helper is missing"
    source = SINGULAR_SOURCE.read_text(encoding="utf-8")

    assert "leftoverMapPlotTickAxisBadge" in source
    assert "leftover-map axis {axis} tick {value} {share}%" in source
    assert "leftover-map axis {axis} tick {value} σ {singular} {share}%" in source


def test_report_graphic_tick_never_infers_share_from_singular() -> None:
    """Share-only, singular-only, combined, and empty states remain persisted-data decisions."""
    assert SINGULAR_SOURCE.exists(), "report graphic axis projection helper is missing"
    source = SINGULAR_SOURCE.read_text(encoding="utf-8")

    assert "Number.isFinite" in source
    assert "leftover_share" in source
    assert "formatLeftoverMapPlotAxisSingular" in source
    assert "Math.sqrt" not in source
    assert "Math.max" not in source
