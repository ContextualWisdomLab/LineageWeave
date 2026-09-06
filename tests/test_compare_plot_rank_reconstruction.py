"""Executable reconstruction contract for #858 on the current #857 parent."""

from pathlib import Path


_ROOT = Path(__file__).parents[1]


def test_current_parent_receives_rank_adr_without_losing_expected_contract() -> None:
    """Rank is an additive successor of the current expected-caption contract."""
    rank_adr = _ROOT / "docs" / "adr" / "0318-leftover-map-compare-plot-rank.md"
    assert rank_adr.exists()

    expected_adr = (_ROOT / "docs" / "adr" / "0317-leftover-map-compare-plot-expected.md").read_text(
        encoding="utf-8"
    )
    assert "leftover expected" in expected_adr.lower()

    layout = (_ROOT / "frontend" / "src" / "leftoverMapPlotLayout.ts").read_text(encoding="utf-8")
    plot = (_ROOT / "frontend" / "src" / "components" / "LeftoverMapPlot.tsx").read_text(
        encoding="utf-8"
    )
    assert "LEFTOVER_MAP_COMPARE_PLOT_SEGMENT_RANK" in layout
    assert "LEFTOVER_MAP_COMPARE_PLOT_SEGMENT_EXPECTED" in layout
    assert "LEFTOVER_MAP_COMPARE_PLOT_SEGMENT_RANK" in plot
    assert "LEFTOVER_MAP_COMPARE_PLOT_SEGMENT_EXPECTED" in plot


def test_rank_successor_advances_all_runtime_version_surfaces() -> None:
    """The reconstructed successor must remain one coherent v2.75.0 product."""
    assert 'version = "2.75.0"' in (_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    assert '"version": "2.75.0"' in (_ROOT / "frontend" / "package.json").read_text(
        encoding="utf-8"
    )
    assert '__version__ = "2.75.0"' in (_ROOT / "lineageweave" / "__init__.py").read_text(
        encoding="utf-8"
    )
