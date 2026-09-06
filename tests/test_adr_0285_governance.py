"""Governance regression for the draft ADR 0285 decision state."""

from pathlib import Path


ADR_PATH = Path(__file__).parents[1] / "docs/adr/0285-leftover-map-list-item-coverage.md"


def test_draft_adr_0285_remains_proposed() -> None:
    """Keep the unmerged decision proposed until independent acceptance exists."""
    text = ADR_PATH.read_text(encoding="utf-8")
    assert "**Decision status:** Proposed" in text
    assert "**Decision status:** Accepted" not in text
