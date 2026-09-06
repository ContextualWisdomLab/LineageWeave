"""Governance regression for the draft ADR 0286 decision state."""

from pathlib import Path


ADR_PATH = Path(__file__).parents[1] / "docs/adr/0286-leftover-map-list-incomplete-post.md"


def test_draft_adr_0286_remains_proposed() -> None:
    """Keep the unmerged decision proposed until independent acceptance exists."""
    text = ADR_PATH.read_text(encoding="utf-8")
    assert "**Decision status:** Proposed" in text
    assert "**Decision status:** Accepted" not in text
