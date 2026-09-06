"""Governance contract for the grouping-comparison graphic ADR state."""

from pathlib import Path


_ADR = (
    Path(__file__).parents[1]
    / "docs"
    / "adr"
    / "0304-leftover-map-compare-graphic.md"
)


def test_compare_graphic_adr_remains_proposed_until_independent_acceptance() -> None:
    """A Draft candidate cannot claim an accepted architecture decision."""
    text = _ADR.read_text(encoding="utf-8")
    assert text.startswith("# ADR 0304")
    assert "**Decision status:** Proposed" in text
    assert "**Decision status:** Accepted" not in text
