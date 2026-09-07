from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_reconstruction_comparison_uses_distinct_proposed_adr_0295() -> None:
    assert (ROOT / "docs/adr/0294-leftover-map-compare-incomplete-item.md").exists()
    path = ROOT / "docs/adr/0295-leftover-map-compare-reconstruction.md"
    assert path.exists()
    text = path.read_text(encoding="utf-8")
    assert text.startswith("# ADR 0295 —")
    assert "**Decision status:** Proposed" in text
    assert "**Decision status:** Accepted" not in text
    assert "accessible name" in text
    assert "fast-mlsirm" in text
