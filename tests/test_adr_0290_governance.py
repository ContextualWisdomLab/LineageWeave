"""Governance regression for reconstructed grouping-comparison coverage."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_grouping_comparison_coverage_uses_distinct_proposed_adr_0290() -> None:
    """Keep #821 off #820's ADR 0289 and Proposed until independent acceptance."""
    singular = ROOT / "docs/adr/0289-leftover-map-plot-singular.md"
    old_collision = ROOT / "docs/adr/0289-leftover-map-compare-coverage.md"
    coverage = ROOT / "docs/adr/0290-leftover-map-compare-coverage.md"
    assert singular.exists()
    assert not old_collision.exists()
    text = coverage.read_text(encoding="utf-8")
    assert text.startswith("# ADR 0290 —")
    assert "**Decision status:** Proposed" in text
    assert "**Decision status:** Accepted" not in text
