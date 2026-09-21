"""Governance regression for grouping-comparison item coverage."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_grouping_comparison_item_coverage_uses_distinct_proposed_adr_0291() -> None:
    """Keep #822 distinct from #821 ADR 0290 and Proposed while Draft."""
    post_coverage = ROOT / "docs/adr/0290-leftover-map-compare-coverage.md"
    old_collision = ROOT / "docs/adr/0290-leftover-map-compare-item-coverage.md"
    item_coverage = ROOT / "docs/adr/0291-leftover-map-compare-item-coverage.md"
    assert post_coverage.exists()
    assert not old_collision.exists()
    text = item_coverage.read_text(encoding="utf-8")
    assert text.startswith("# ADR 0291 —")
    assert "**Decision status:** Proposed" in text
    assert "**Decision status:** Accepted" not in text
