"""Executable contract for persisted singular values on the comparison graphic."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PLOT_SOURCE = ROOT / "frontend" / "src" / "components" / "LeftoverMapPlot.tsx"
SINGULAR_SOURCE = ROOT / "frontend" / "src" / "leftoverMapPlotAxisSingular.ts"
APP_TEST_SOURCE = ROOT / "frontend" / "src" / "App.test.tsx"


def test_comparison_graphic_has_distinct_persisted_singular_value_copy() -> None:
    """Comparison-axis σ copy must remain distinct from report, strip, share, and tick copy."""
    assert SINGULAR_SOURCE.exists(), (
        "comparison graphic singular-value helper is missing; do not infer σ from axis share"
    )
    singular_source = SINGULAR_SOURCE.read_text(encoding="utf-8")
    plot_source = PLOT_SOURCE.read_text(encoding="utf-8")

    assert (
        'export const LEFTOVER_MAP_COMPARE_PLOT_AXIS_SINGULAR =\n'
        '  "leftover map comparison axis {axis} (σ {value})";'
        in singular_source
    )
    assert (
        'export const LEFTOVER_MAP_COMPARE_PLOT_AXIS_SINGULAR_SHARE =\n'
        '  "leftover map comparison axis {axis} (σ {value}, {share}%)";'
        in singular_source
    )
    assert "LEFTOVER_MAP_COMPARE_PLOT_AXIS_SINGULAR" in plot_source
    assert "LEFTOVER_MAP_COMPARE_PLOT_AXIS_SINGULAR_SHARE" in plot_source


def test_singular_value_is_read_from_axis_evidence_and_fails_closed() -> None:
    """Persisted σ=0 stays explicit; missing, non-finite, or negative σ omits independently."""
    assert SINGULAR_SOURCE.exists(), "persisted singular-value projection helper is missing"
    singular_source = SINGULAR_SOURCE.read_text(encoding="utf-8")

    assert "leftover_singular_value" in singular_source
    assert "Number.isFinite" in singular_source
    assert "< 0" in singular_source
    assert "return null" in singular_source
    assert ".toFixed(2)" in singular_source
    assert "leftover_share" not in singular_source
    assert "Math.max" not in singular_source
    assert "Math.min" not in singular_source


def test_app_acceptance_requires_exact_comparison_sigma_and_share_copy() -> None:
    """App acceptance must assert the persisted comparison σ and share together, exactly."""
    app_test_source = APP_TEST_SOURCE.read_text(encoding="utf-8")

    stale_share_only = (
        '"leftover map comparison axis 1 (82%)"',
        '"leftover map comparison axis 2 (18%)"',
    )
    expected_sigma_share = (
        '"leftover map comparison axis 1 (σ 1.84, 82%)"',
        '"leftover map comparison axis 2 (σ 0.86, 18%)"',
    )

    for stale_copy in stale_share_only:
        assert stale_copy not in app_test_source, (
            "comparison-axis App acceptance still asserts pre-ADR-0321 share-only copy"
        )
    for expected_copy in expected_sigma_share:
        assert app_test_source.count(expected_copy) >= 2, (
            "comparison-axis App acceptance must cover exact σ+share copy in both report and "
            "grouping-comparison integration paths"
        )
