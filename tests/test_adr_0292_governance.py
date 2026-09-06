"""Governance regression for leftover-axis singular-value badges."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def test_axis_singular_badges_use_distinct_proposed_adr_0292() -> None:
    """Keep #823 distinct from #821/#822 decisions and Proposed while Draft."""
    assert (ROOT / "docs/adr/0290-leftover-map-compare-coverage.md").exists()
    assert (ROOT / "docs/adr/0291-leftover-map-compare-item-coverage.md").exists()
    assert not (ROOT / "docs/adr/0290-leftover-map-axis-singular.md").exists()
    successor = ROOT / "docs/adr/0292-leftover-map-axis-singular.md"
    assert successor.exists()
    text = successor.read_text(encoding="utf-8")
    assert text.startswith("# ADR 0292 —")
    assert "**Decision status:** Proposed" in text
    assert "**Decision status:** Accepted" not in text
