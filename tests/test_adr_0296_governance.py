from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def test_explained_share_comparison_uses_distinct_proposed_adr_0296() -> None:
    assert (ROOT/'docs/adr/0295-leftover-map-compare-reconstruction.md').exists()
    text=(ROOT/'docs/adr/0296-leftover-map-compare-explained-share.md').read_text(encoding='utf-8')
    assert '**Decision status:** Proposed' in text
    assert '**Decision status:** Accepted' not in text
    assert 'accessible name' in text and 'fast-mlsirm' in text
