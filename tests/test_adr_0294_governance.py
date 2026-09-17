from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_incomplete_item_comparison_uses_distinct_proposed_adr_0294() -> None:
    assert (ROOT / "docs/adr/0293-leftover-map-compare-incomplete-post.md").exists()
    path = ROOT / "docs/adr/0294-leftover-map-compare-incomplete-item.md"
    assert path.exists()
    text = path.read_text(encoding="utf-8")
    assert text.startswith("# ADR 0294 —")
    assert "**Decision status:** Proposed" in text
    assert "**Decision status:** Accepted" not in text
    assert "full persisted grouping" in text and "Partial visibility" in text
