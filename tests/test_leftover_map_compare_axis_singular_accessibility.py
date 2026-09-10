from pathlib import Path


APP_SOURCE = Path(__file__).parents[1] / "frontend" / "src" / "App.tsx"


def test_grouping_comparison_singular_badge_does_not_name_generic_span() -> None:
    """Keep persisted sigma visible without an ARIA name on a generic span."""
    source = APP_SOURCE.read_text(encoding="utf-8")
    marker = "{comparisonAxisSingular !== null ? ("
    assert marker in source
    singular_block = source.split(marker, 1)[1].split(") : null}", 1)[0]

    assert 'className="post-badge"' in singular_block
    assert "LEFTOVER_MAP_COMPARE_AXIS_SINGULAR, comparisonAxisSingular" in singular_block
    assert "aria-label=" not in singular_block
