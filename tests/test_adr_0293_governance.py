from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
def test_incomplete_post_comparison_uses_distinct_proposed_adr_0293() -> None:
    assert (ROOT/'docs/adr/0290-leftover-map-compare-coverage.md').exists()
    assert (ROOT/'docs/adr/0291-leftover-map-compare-item-coverage.md').exists()
    assert (ROOT/'docs/adr/0292-leftover-map-axis-singular.md').exists()
    assert not (ROOT/'docs/adr/0291-leftover-map-compare-incomplete-post.md').exists()
    p=ROOT/'docs/adr/0293-leftover-map-compare-incomplete-post.md'
    assert p.exists()
    text=p.read_text(encoding='utf-8')
    assert text.startswith('# ADR 0293 —')
    assert '**Decision status:** Proposed' in text
    assert '**Decision status:** Accepted' not in text
    assert 'full persisted grouping' in text and 'partial' in text.lower()
