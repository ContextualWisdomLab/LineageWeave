"""Executable contract for persisted singular values on report-axis badges."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BADGE_SOURCE = ROOT / "frontend" / "src" / "leftoverMapAxisBadge.ts"
SINGULAR_SOURCE = ROOT / "frontend" / "src" / "leftoverMapPlotAxisSingular.ts"


def test_report_axis_badge_keeps_singular_value_and_share_semantically_distinct() -> None:
    """Report badges must expose persisted σ without borrowing comparison-graphic copy."""
    assert BADGE_SOURCE.exists(), "report-axis singular-value badge helper is missing"
    badge_source = BADGE_SOURCE.read_text(encoding="utf-8")

    assert 'LEFTOVER_MAP_AXIS_BADGE_SHARE = "leftover axis {axis} {share}%"' in badge_source
    assert (
        'LEFTOVER_MAP_AXIS_BADGE_SINGULAR = "leftover axis {axis} σ {value} {share}%"'
        in badge_source
    )
    assert "leftoverSingularForAxis" in badge_source
    assert "formatLeftoverMapPlotAxisSingular" in badge_source
    assert "leftover map comparison graphic" not in badge_source


def test_report_axis_badge_never_infers_singular_value_from_share() -> None:
    """Missing or invalid σ omits independently while rank-0 σ=0 stays representable."""
    assert BADGE_SOURCE.exists(), "report-axis singular-value badge helper is missing"
    assert SINGULAR_SOURCE.exists(), "persisted singular-value helper is missing"
    badge_source = BADGE_SOURCE.read_text(encoding="utf-8")
    singular_source = SINGULAR_SOURCE.read_text(encoding="utf-8")

    assert "leftover_singular_value" in singular_source
    assert "Number.isFinite" in singular_source
    assert "< 0" in singular_source
    assert ".toFixed(2)" in singular_source
    assert "Math.sqrt" not in badge_source
    assert "Math.sqrt" not in singular_source
