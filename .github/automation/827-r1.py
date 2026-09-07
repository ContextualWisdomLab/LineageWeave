from pathlib import Path
import json


def one(path: str, old: str, new: str) -> None:
    p=Path(path); text=p.read_text(); c=text.count(old)
    if c != 1: raise SystemExit(f"{path}: anchor count={c}: {old[:120]!r}")
    p.write_text(text.replace(old,new,1))

one('frontend/src/leftoverMapExplainedShare.ts',
    'export const LEFTOVER_MAP_EXPLAINED_SHARE_ACTION =\n  "Leftover map leaves explained leftover share {value} of raw residual after IRT main effects. Open this post to read {criterion}.";\n',
    'export const LEFTOVER_MAP_EXPLAINED_SHARE_ACTION =\n  "Leftover map leaves explained leftover share {value} of raw residual after IRT main effects. Open this post to read {criterion}.";\n\nexport const LEFTOVER_MAP_COMPARE_EXPLAINED_SHARE_LABEL =\n  "Leftover map comparison explained leftover share";\n')
one('frontend/src/App.tsx',
    'import {\n  formatLeftoverMapReconstruction,\n  LEFTOVER_MAP_COMPARE_RECONSTRUCTION_LABEL,\n} from "./leftoverMapReconstruction";\n',
    'import {\n  formatLeftoverMapReconstruction,\n  LEFTOVER_MAP_COMPARE_RECONSTRUCTION_LABEL,\n} from "./leftoverMapReconstruction";\nimport {\n  formatLeftoverMapExplainedShare,\n  LEFTOVER_MAP_COMPARE_EXPLAINED_SHARE_LABEL,\n} from "./leftoverMapExplainedShare";\n')
one('frontend/src/App.tsx',
    '                    const reconstruction = formatLeftoverMapReconstruction(\n                      pair.leftover_map_reconstruction,\n                    );\n                    const pairAccessibleName = `Open leftover ${pair.pair_kind} pair from comparison: ${pair.post_title} · ${criterion}${\n                      reconstruction\n                        ? ` · ${t(LEFTOVER_MAP_COMPARE_RECONSTRUCTION_LABEL)} ${reconstruction}`\n                        : ""\n                    }`;\n',
    '                    const reconstruction = formatLeftoverMapReconstruction(\n                      pair.leftover_map_reconstruction,\n                    );\n                    const explainedShare = formatLeftoverMapExplainedShare(\n                      pair.leftover_map_explained_share,\n                    );\n                    const pairAccessibleName = `Open leftover ${pair.pair_kind} pair from comparison: ${pair.post_title} · ${criterion}${\n                      reconstruction\n                        ? ` · ${t(LEFTOVER_MAP_COMPARE_RECONSTRUCTION_LABEL)} ${reconstruction}`\n                        : ""\n                    }${\n                      explainedShare\n                        ? ` · ${t(LEFTOVER_MAP_COMPARE_EXPLAINED_SHARE_LABEL)} ${explainedShare}`\n                        : ""\n                    }`;\n')
one('frontend/src/App.tsx',
    '                          {reconstruction ? (\n                            <span className="post-badge" aria-hidden="true">\n                              {reconstruction}\n                            </span>\n                          ) : null}\n',
    '                          {reconstruction ? (\n                            <span className="post-badge" aria-hidden="true">\n                              {reconstruction}\n                            </span>\n                          ) : null}\n                          {explainedShare ? (\n                            <span className="post-badge" aria-hidden="true">\n                              {explainedShare}\n                            </span>\n                          ) : null}\n')

fixture='''                    post_id: "post-1",\n                    post_title: "Public post",\n                    criterion_code: "sales_lead_specificity",\n                    leftover_distance: 0.12,\n                    leftover_residual: 0.4,\n                    leftover_map_reconstruction: 0.248,\n'''
p=Path('frontend/src/App.test.tsx'); text=p.read_text(); c=text.count(fixture)
if c != 1: raise SystemExit(f'comparison fixture count={c}')
p.write_text(text.replace(fixture, fixture+'                    leftover_map_explained_share: 0.76,\n'))
one('frontend/src/App.test.tsx',
    '    expect(reconstructionPair).toHaveTextContent("R̂ +0.25");\n',
    '    expect(reconstructionPair).toHaveTextContent("R̂ +0.25");\n    const explainedSharePair = screen.getByRole("button", {\n      name: /open leftover closest pair from comparison: public post.*leftover map comparison reconstruction R̂ \\+0\\.25.*leftover map comparison explained leftover share R̂²\\/R² 0\\.76/i,\n    });\n    expect(explainedSharePair).toHaveTextContent("R̂²/R² 0.76");\n')

p=Path('frontend/src/i18n.ts'); text=p.read_text()
for old,new in [
('"Leftover map comparison reconstruction": "잔여 지도 비교 재구성",','"Leftover map comparison reconstruction": "잔여 지도 비교 재구성",\n    "Leftover map comparison explained leftover share": "잔여 지도 비교 설명 잔여 비율",'),
('"Leftover map comparison reconstruction": "残差地图比较重建",','"Leftover map comparison reconstruction": "残差地图比较重建",\n    "Leftover map comparison explained leftover share": "残差地图比较已解释残差占比",'),
('"Leftover map comparison reconstruction": "残差マップの比較再構成",','"Leftover map comparison reconstruction": "残差マップの比較再構成",\n    "Leftover map comparison explained leftover share": "残差マップの比較説明済み残差比率",'),
('"Leftover map comparison reconstruction": "Tái dựng so sánh bản đồ phần dư",','"Leftover map comparison reconstruction": "Tái dựng so sánh bản đồ phần dư",\n    "Leftover map comparison explained leftover share": "Tỷ phần phần dư được giải thích khi so sánh bản đồ phần dư",')]:
    if text.count(old)!=1: raise SystemExit(f'i18n anchor count={text.count(old)}')
    text=text.replace(old,new,1)
p.write_text(text)
p=Path('frontend/src/i18n.test.ts'); text=p.read_text()
old='    "Leftover map comparison reconstruction",\n    "Leftover-map graphic item coverage",'
if text.count(old)!=1: raise SystemExit(f'i18n test anchor count={text.count(old)}')
p.write_text(text.replace(old,'    "Leftover map comparison reconstruction",\n    "Leftover map comparison explained leftover share",\n    "Leftover-map graphic item coverage",',1))

one('pyproject.toml','version = "2.52.0"','version = "2.53.0"')
one('lineageweave/__init__.py','__version__ = "2.52.0"','__version__ = "2.53.0"')
p=Path('frontend/package.json'); data=json.loads(p.read_text()); assert data['version']=='2.52.0'; data['version']='2.53.0'; p.write_text(json.dumps(data,indent=2,ensure_ascii=False)+'\n')
one('CHANGELOG.md','## [Unreleased]\n\n### Added\n\n','## [Unreleased]\n\n### Added\n\n- Grouping comparison pair buttons now expose persisted explained-leftover share `e = R̂²/R²` (ADR 0296 / v2.53.0). The visible duplicate badge is accessibility-hidden while the actionable button name includes the localized label and formatted persisted value. Missing/non-finite `e` omits only the suffix; finite zero and values above 1 remain explicit without clamping or client-side derivation.\n\n')
Path('CHANGELOG.d/2.53.0-leftover-map-compare-explained-share.md').write_text('''## 2.53.0 — Grouping comparison explained-leftover share\n\n- Show persisted `e = R̂²/R²` on grouping-comparison pair buttons (ADR 0296).\n- Put the localized metric/value in the button accessible name; the duplicate visible badge is `aria-hidden`.\n- Missing/non-finite values omit only this metric; zero and values above 1 are preserved and no proxy is derived.\n''')
Path('docs/adr/0296-leftover-map-compare-explained-share.md').write_text('''# ADR 0296 — Grouping comparison explained-leftover share\n\n**Decision status:** Proposed\n\n## Problem\nThe serialized comparison surface omits persisted explained-leftover share `e = R̂²/R²`. The historical implementation rendered a descendant badge inside a button with an explicit accessible name, so the visible metric was not reliably announced as part of the action.\n\n## Decision\nFormat only persisted `leftover_map_explained_share` through `formatLeftoverMapExplainedShare`. Append the localized label and formatted value to the pair button accessible name, and mark the duplicate visible badge `aria-hidden`. Missing/non-finite values omit only this suffix; finite zero and values above 1 remain explicit. Never derive or clamp `e` from `R̂`, `R`, distance, coordinates, residuals, rank, coverage, or visible-subset proxies. fast-mlsirm remains psychometric owner.\n\nThis ADR remains Proposed while Draft. Acceptance requires current-head hosted tests, rendered keyboard/screen-reader/a11y evidence, canonical eight-locale ledger convergence, independent approval, and normal protected-branch merge.\n''')
Path('tests/test_adr_0296_governance.py').write_text('''from pathlib import Path\nROOT=Path(__file__).resolve().parents[1]\ndef test_explained_share_comparison_uses_distinct_proposed_adr_0296() -> None:\n    assert (ROOT/'docs/adr/0295-leftover-map-compare-reconstruction.md').exists()\n    text=(ROOT/'docs/adr/0296-leftover-map-compare-explained-share.md').read_text(encoding='utf-8')\n    assert '**Decision status:** Proposed' in text\n    assert '**Decision status:** Accepted' not in text\n    assert 'accessible name' in text and 'fast-mlsirm' in text\n''')
for path,block in {
'AGENTS.md':'ADR 0296 adds persisted grouping-comparison explained-leftover share `e` in the LineageWeave read-model/UI boundary: expose it in the pair button accessible name, keep the duplicate visible badge presentation-only, and never derive or clamp psychometric values.',
'ARCHITECTURE.md':'ADR 0296 adds persisted explained-leftover share `e = R̂²/R²` to grouping-comparison pair actions; the button accessible name is authoritative for assistive technology and fast-mlsirm remains psychometric owner.',
'CLAUDE.md':'ADR 0296 is the Proposed grouping-comparison explained-share contract: persisted `e` only, accessible-name exposure required, no client derivation or clamping.',
'docs/product-technical-gap-baseline.md':'### 2026-09-07 — #827 exact-parent reconstruction candidate\n\nExact parent `#826@66a7750a10ad0e9526716d382707f99528a75d90` omits persisted grouping-comparison explained-leftover share. ADR 0296 / v2.53.0 restores that valid delta and fixes its historical accessible-name defect. Candidate evidence is not protected-main/release evidence; current-head browser/screen-reader/a11y, canonical eight-locale ledger consumption, independent review, and normal protected merge remain outstanding.'}.items():
    p=Path(path); t=p.read_text()
    if block not in t: p.write_text(t.rstrip()+'\n\n'+block+'\n')
