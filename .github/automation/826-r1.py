from pathlib import Path
import json


def replace_once(path: str, old: str, new: str) -> None:
    p = Path(path)
    text = p.read_text()
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{path}: expected one anchor, got {count}: {old[:120]!r}")
    p.write_text(text.replace(old, new, 1))


# Historical product delta: expose persisted R-hat on grouping-comparison pair rows.
replace_once(
    "frontend/src/leftoverMapReconstruction.ts",
    'export const LEFTOVER_MAP_RECONSTRUCTION_ACTION =\n  "Leftover map reconstructs R̂ {value} after IRT main effects. Open this post to read {criterion}.";\n',
    'export const LEFTOVER_MAP_RECONSTRUCTION_ACTION =\n  "Leftover map reconstructs R̂ {value} after IRT main effects. Open this post to read {criterion}.";\n\nexport const LEFTOVER_MAP_COMPARE_RECONSTRUCTION_LABEL =\n  "Leftover map comparison reconstruction";\n',
)
replace_once(
    "frontend/src/App.tsx",
    'import "./App.css";\n',
    'import {\n  formatLeftoverMapReconstruction,\n  LEFTOVER_MAP_COMPARE_RECONSTRUCTION_LABEL,\n} from "./leftoverMapReconstruction";\nimport "./App.css";\n',
)
replace_once(
    "frontend/src/App.tsx",
    '                    const criterion = criterionShortLabel(pair.criterion_code);\n                    return (\n',
    '                    const criterion = criterionShortLabel(pair.criterion_code);\n                    const reconstruction = formatLeftoverMapReconstruction(\n                      pair.leftover_map_reconstruction,\n                    );\n                    const pairAccessibleName = `Open leftover ${pair.pair_kind} pair from comparison: ${pair.post_title} · ${criterion}${\n                      reconstruction\n                        ? ` · ${t(LEFTOVER_MAP_COMPARE_RECONSTRUCTION_LABEL)} ${reconstruction}`\n                        : ""\n                    }`;\n                    return (\n',
)
replace_once(
    "frontend/src/App.tsx",
    '                          aria-label={`Open leftover ${pair.pair_kind} pair from comparison: ${pair.post_title} · ${criterion}`}\n',
    '                          aria-label={pairAccessibleName}\n',
)
replace_once(
    "frontend/src/App.tsx",
    '                          <span className="post-badge">d {pair.leftover_distance.toFixed(2)}</span>\n',
    '                          <span className="post-badge">d {pair.leftover_distance.toFixed(2)}</span>\n                          {reconstruction ? (\n                            <span className="post-badge" aria-hidden="true">\n                              {reconstruction}\n                            </span>\n                          ) : null}\n',
)

# Current exact-parent fixture gets one finite persisted value. The accessible-name
# assertion is the realistic repair for the unresolved review finding: a visual
# descendant inside an aria-labelled button must not be the only semantic exposure.
replace_once(
    "frontend/src/App.test.tsx",
    '                    leftover_distance: 0.12,\n                    leftover_residual: 0.4,\n',
    '                    leftover_distance: 0.12,\n                    leftover_residual: 0.4,\n                    leftover_map_reconstruction: 0.248,\n',
)
replace_once(
    "frontend/src/App.test.tsx",
    '    ).toHaveTextContent("Closest leftover: Public post · sales-lead");\n',
    '    ).toHaveTextContent("Closest leftover: Public post · sales-lead");\n    const reconstructionPair = screen.getByRole("button", {\n      name: /open leftover closest pair from comparison: public post.*leftover map comparison reconstruction R̂ \\+0\\.25/i,\n    });\n    expect(reconstructionPair).toHaveTextContent("R̂ +0.25");\n',
)

# Inline compatibility copy remains bounded to the legacy four locales; canonical
# eight-locale translation authority stays with the separate ledger owner path.
p = Path("frontend/src/i18n.ts")
text = p.read_text()
for old, new in [
    ('"Leftover map comparison incomplete items": "잔여 지도 비교 불완전 기준",', '"Leftover map comparison incomplete items": "잔여 지도 비교 불완전 기준",\n    "Leftover map comparison reconstruction": "잔여 지도 비교 재구성",'),
    ('"Leftover map comparison incomplete items": "残差地图比较不完整准则",', '"Leftover map comparison incomplete items": "残差地图比较不完整准则",\n    "Leftover map comparison reconstruction": "残差地图比较重建",'),
    ('"Leftover map comparison incomplete items": "残差マップの比較不完全基準",', '"Leftover map comparison incomplete items": "残差マップの比較不完全基準",\n    "Leftover map comparison reconstruction": "残差マップの比較再構成",'),
    ('"Leftover map comparison incomplete items": "Tiêu chí không đầy đủ so sánh trên bản đồ phần dư",', '"Leftover map comparison incomplete items": "Tiêu chí không đầy đủ so sánh trên bản đồ phần dư",\n    "Leftover map comparison reconstruction": "Tái dựng so sánh bản đồ phần dư",'),
]:
    if text.count(old) != 1:
        raise SystemExit(f"i18n anchor count={text.count(old)}: {old}")
    text = text.replace(old, new, 1)
p.write_text(text)

p = Path("frontend/src/i18n.test.ts")
text = p.read_text()
old = '    "Leftover map comparison incomplete items",\n    "Leftover-map graphic item coverage",'
if text.count(old) != 1:
    raise SystemExit(f"i18n required-label anchor count={text.count(old)}")
text = text.replace(
    old,
    '    "Leftover map comparison incomplete items",\n    "Leftover map comparison reconstruction",\n    "Leftover-map graphic item coverage",',
    1,
)
p.write_text(text)

# Collision-free serialized identity.
replace_once("pyproject.toml", 'version = "2.51.0"', 'version = "2.52.0"')
replace_once("lineageweave/__init__.py", '__version__ = "2.51.0"', '__version__ = "2.52.0"')
p = Path("frontend/package.json")
data = json.loads(p.read_text())
if data.get("version") != "2.51.0":
    raise SystemExit(f"frontend version drift={data.get('version')}")
data["version"] = "2.52.0"
p.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")

entry = '- Grouping comparison leftover-pair buttons now expose persisted leftover-map reconstruction `R̂` (ADR 0295 / v2.52.0). The visible badge is decorative to accessibility APIs; the button accessible name carries the reconstruction label and value, so the explicit button `aria-label` cannot suppress the metric. Missing/non-finite `R̂` omits only that value and no client-side proxy is invented.\n\n'
replace_once("CHANGELOG.md", "## [Unreleased]\n\n### Added\n\n", "## [Unreleased]\n\n### Added\n\n" + entry)
Path("CHANGELOG.d/2.52.0-leftover-map-compare-reconstruction.md").write_text("""## 2.52.0 — Grouping comparison leftover-map reconstruction

- Show persisted leftover-map reconstruction `R̂` on grouping-comparison pair buttons (ADR 0295).
- Include the admitted reconstruction label/value in the button accessible name; keep the visible badge `aria-hidden` so it is not double-announced.
- Missing or non-finite values omit only the reconstruction; do not derive `R̂` from distance, coordinates, residuals, rank, coverage, or any other proxy.
""")
Path("docs/adr/0295-leftover-map-compare-reconstruction.md").write_text("""# ADR 0295 — Grouping comparison leftover-map reconstruction

**Decision status:** Proposed

## Problem
Grouping-comparison pair rows already carry persisted `leftover_map_reconstruction`, but buyers cannot see it in the serialized current stack. The historical implementation placed a reconstruction badge inside a button that already had an explicit `aria-label`; that descendant text therefore did not reliably contribute to the button's accessible name.

## Decision
Format only the persisted `leftover_map_reconstruction` through the existing `formatLeftoverMapReconstruction` contract. Render the visible `R̂` badge for sighted comparison, mark that duplicate badge `aria-hidden`, and include the localized comparison-reconstruction label plus formatted value in the pair button's accessible name. Missing or non-finite `R̂` omits only this suffix. Never reconstruct `R̂` from distance, coordinates, residuals, unexplained leftover, rank, coverage counts, or any visible-subset proxy.

This is LineageWeave read-model/UI composition only; fast-mlsirm remains the psychometric owner. ADR status remains Proposed while Draft. Acceptance requires current-head hosted tests, keyboard/screen-reader/browser evidence, canonical eight-locale translation-ledger convergence, independent approval, and normal protected-branch merge.
""")
Path("tests/test_adr_0295_governance.py").write_text("""from pathlib import Path

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
""")
for path, block in {
    "AGENTS.md": "ADR 0295 keeps grouping-comparison reconstruction in the LineageWeave read-model/UI boundary: format only persisted `R̂`, expose the value in the pair button accessible name, and never derive psychometric reconstruction from UI-visible proxies.",
    "ARCHITECTURE.md": "ADR 0295 adds persisted `R̂` to grouping-comparison pair buttons. The explicit button accessible name carries the reconstruction label/value; the visible duplicate badge is presentation-only. Psychometric computation remains owned by fast-mlsirm.",
    "CLAUDE.md": "ADR 0295 is the Proposed grouping-comparison reconstruction contract: persisted `R̂` only, no client inference, accessible-name exposure required despite the button's explicit aria-label.",
    "docs/product-technical-gap-baseline.md": "### 2026-09-07 — #826 exact-parent reconstruction candidate\n\nExact parent `#825@b73b10e3079e77f3e62235b2b709dc8a3f450292` omits persisted `R̂` from grouping-comparison pair rows. ADR 0295 / v2.52.0 restores that valid read-model delta and repairs the historical accessibility defect by carrying the label/value in the button accessible name. Candidate evidence is not protected-main/release evidence; current-head browser/screen-reader/a11y, canonical eight-locale ledger consumption, independent review, and normal protected merge remain outstanding.",
}.items():
    p = Path(path)
    text = p.read_text()
    if block not in text:
        p.write_text(text.rstrip() + "\n\n" + block + "\n")
