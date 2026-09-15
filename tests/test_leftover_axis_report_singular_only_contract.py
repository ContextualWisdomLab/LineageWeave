"""Executable contract for the report-axis singular-only state."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BADGE_SOURCE = ROOT / "frontend" / "src" / "leftoverMapAxisBadge.ts"
APP_SOURCE = ROOT / "frontend" / "src" / "App.tsx"


def test_report_axis_badge_preserves_singular_when_share_is_missing() -> None:
    """A valid persisted σ remains visible when axis share is absent."""
    assert BADGE_SOURCE.exists(), "report-axis singular-value badge helper is missing"
    source = BADGE_SOURCE.read_text(encoding="utf-8")

    assert (
        'LEFTOVER_MAP_AXIS_BADGE_SINGULAR_ONLY = "leftover axis {axis} σ {value}"'
        in source
    )
    assert 'LEFTOVER_MAP_AXIS_BADGE_SINGULAR = "leftover axis {axis} σ {value}{share}"' in source
    assert "formatLeftoverMapPlotAxisShare" in source
    assert 'return share === null ? "" : ` ${share}%`;' in source
    assert "Number.NaN" not in source


def test_report_axis_badge_keeps_sigma_and_share_missingness_independent() -> None:
    """σ-only, share-only, combined, and empty states must remain data-driven."""
    assert BADGE_SOURCE.exists(), "report-axis singular-value badge helper is missing"
    source = BADGE_SOURCE.read_text(encoding="utf-8")

    assert "formatLeftoverMapPlotAxisSingular" in source
    assert "leftoverMapAxisBadgeShare" in source
    assert "LEFTOVER_MAP_AXIS_BADGE_SINGULAR" in source
    assert "LEFTOVER_MAP_AXIS_BADGE_SHARE" in source
    assert "LEFTOVER_MAP_AXIS_BADGE_SINGULAR_ONLY" in source
    assert 'singular === null && share === ""' in source
    assert 'share === ""' in source
    assert "Math.sqrt" not in source


def test_report_axis_rendering_consumes_the_four_state_projection() -> None:
    """The report path must omit a badge when neither persisted axis datum is usable."""
    app_source = APP_SOURCE.read_text(encoding="utf-8")

    assert "leftoverMapAxisBadge," in app_source
    assert "const badge = leftoverMapAxisBadge(axis);" in app_source
    assert "badge === null ? null" in app_source
    assert "tf(badge.template, badge.values)" in app_source
    assert "leftoverMapAxisBadgeShare," not in app_source
    assert "leftoverMapAxisBadgeSingular," not in app_source
