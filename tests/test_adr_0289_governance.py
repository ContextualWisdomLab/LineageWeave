"""Governance regression for draft ADR 0289."""

from pathlib import Path

ADR_PATH = Path(__file__).parents[1] / "docs/adr/0289-leftover-map-plot-singular.md"

def test_draft_adr_0289_remains_proposed() -> None:
    """Keep the unmerged decision proposed until independent acceptance exists."""
    text = ADR_PATH.read_text(encoding="utf-8")
    assert "**Decision status:** Proposed" in text
    assert "**Decision status:** Accepted" not in text
