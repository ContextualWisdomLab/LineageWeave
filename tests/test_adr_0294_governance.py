from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def test_adr_0294_is_unique_proposed_successor() -> None:
    expected={290:'0290-leftover-map-compare-coverage.md',291:'0291-leftover-map-compare-item-coverage.md',292:'0292-leftover-map-axis-singular.md',293:'0293-leftover-map-compare-incomplete-post.md',294:'0294-leftover-map-compare-incomplete-item.md'}
    for n,name in expected.items():
        matches=list((ROOT/'docs/adr').glob(f'{n:04d}-*.md'))
        assert len(matches)==1,(n,matches)
        assert matches[0].name==name
    text=(ROOT/'docs/adr/0294-leftover-map-compare-incomplete-item.md').read_text()
    assert '**Decision status:** Proposed' in text
    assert 'full persisted grouping population' in text
    assert 'visible subset' in text
