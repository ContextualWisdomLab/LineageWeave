from pathlib import Path
import json


def replace_once(path: str, old: str, new: str) -> None:
    p = Path(path)
    text = p.read_text()
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{path}: expected one anchor, got {count}: {old[:120]!r}")
    p.write_text(text.replace(old, new, 1))


test_path = Path("frontend/src/App.test.tsx")
text = test_path.read_text()
anchor = '''    expect(
      within(screen.getByLabelText("Grouping comparison")).queryByLabelText("Leftover map incomplete items"),
    ).not.toBeInTheDocument();
'''
addition = '''    expect(
      within(screen.getByLabelText("Grouping comparison")).getAllByLabelText(
        "Leftover map comparison incomplete items",
      ),
    ).toHaveLength(2);
    expect(
      within(screen.getByLabelText("Grouping comparison")).getAllByLabelText(
        "Leftover map comparison incomplete items",
      )[0],
    ).toHaveTextContent("Leftover map dropped 0 incomplete criteria");
    expect(
      within(screen.getByLabelText("Grouping comparison")).getAllByLabelText(
        "Leftover map comparison incomplete items",
      )[1],
    ).toHaveTextContent("Leftover map dropped 1 incomplete criteria");
    expect(
      within(screen.getByLabelText("Grouping comparison")).queryByLabelText(
        "Leftover-map graphic incomplete items",
      ),
    ).not.toBeInTheDocument();
'''
if text.count(anchor) != 1:
    raise SystemExit(f"App.test exact anchor count={text.count(anchor)}")
test_path.write_text(text.replace(anchor, anchor + addition, 1))

replace_once(
    "frontend/src/leftoverMapCoverage.ts",
    'export const LEFTOVER_MAP_COMPARE_INCOMPLETE_POST_LABEL = "Leftover map comparison incomplete posts";\n',
    'export const LEFTOVER_MAP_COMPARE_INCOMPLETE_POST_LABEL = "Leftover map comparison incomplete posts";\n\nexport const LEFTOVER_MAP_COMPARE_INCOMPLETE_ITEM_LABEL = "Leftover map comparison incomplete items";\n',
)
replace_once("frontend/src/leftoverMapCoverage.ts", "ADR 0288 / ADR 0290 / ADR 0291).", "ADR 0288 / ADR 0290 / ADR 0291 / ADR 0294).")

app_path = Path("frontend/src/App.tsx")
app = app_path.read_text()
old = "  LEFTOVER_MAP_COMPARE_INCOMPLETE_POST_LABEL,\n"
if app.count(old) != 1:
    raise SystemExit(f"App import anchor count={app.count(old)}")
app = app.replace(old, old + "  LEFTOVER_MAP_COMPARE_INCOMPLETE_ITEM_LABEL,\n", 1)
old = "            const comparisonIncompletePostCount = leftoverMapIncompletePostCount(row.leftover_map_coverage);\n"
if app.count(old) != 1:
    raise SystemExit(f"App count anchor count={app.count(old)}")
app = app.replace(old, old + "            const comparisonIncompleteItemCount = leftoverMapIncompleteItemCount(row.leftover_map_coverage);\n", 1)
old = '''              {comparisonIncompletePostCount !== null ? (
                <p className="post-meta" role="note" aria-label={t(LEFTOVER_MAP_COMPARE_INCOMPLETE_POST_LABEL)}>
                  {tf(LEFTOVER_MAP_PLOT_INCOMPLETE_POST, comparisonIncompletePostCount)}
                </p>
              ) : null}
'''
new = old + '''              {comparisonIncompleteItemCount !== null ? (
                <p className="post-meta" role="note" aria-label={t(LEFTOVER_MAP_COMPARE_INCOMPLETE_ITEM_LABEL)}>
                  {tf(LEFTOVER_MAP_PLOT_INCOMPLETE_ITEM, comparisonIncompleteItemCount)}
                </p>
              ) : null}
'''
if app.count(old) != 1:
    raise SystemExit(f"App render anchor count={app.count(old)}")
app_path.write_text(app.replace(old, new, 1))

p = Path("frontend/src/i18n.ts")
text = p.read_text()
for old, new in [
    ('"Leftover map comparison incomplete posts": "잔여 지도 비교 불완전 글",', '"Leftover map comparison incomplete posts": "잔여 지도 비교 불완전 글",\n    "Leftover map comparison incomplete items": "잔여 지도 비교 불완전 기준",'),
    ('"Leftover map comparison incomplete posts": "残差地图比较不完整帖文",', '"Leftover map comparison incomplete posts": "残差地图比较不完整帖文",\n    "Leftover map comparison incomplete items": "残差地图比较不完整准则",'),
    ('"Leftover map comparison incomplete posts": "残差マップの比較不完全投稿",', '"Leftover map comparison incomplete posts": "残差マップの比較不完全投稿",\n    "Leftover map comparison incomplete items": "残差マップの比較不完全基準",'),
    ('"Leftover map comparison incomplete posts": "Bài không đầy đủ so sánh trên bản đồ phần dư",', '"Leftover map comparison incomplete posts": "Bài không đầy đủ so sánh trên bản đồ phần dư",\n    "Leftover map comparison incomplete items": "Tiêu chí không đầy đủ so sánh trên bản đồ phần dư",'),
]:
    if text.count(old) != 1:
        raise SystemExit(f"i18n.ts anchor count={text.count(old)}: {old}")
    text = text.replace(old, new, 1)
p.write_text(text)

p = Path("frontend/src/i18n.test.ts")
text = p.read_text()
old = '    "Leftover map comparison incomplete posts",\n    "Leftover-map graphic item coverage",'
if text.count(old) != 1:
    raise SystemExit(f"i18n required-label anchor count={text.count(old)}")
text = text.replace(old, '    "Leftover map comparison incomplete posts",\n    "Leftover map comparison incomplete items",\n    "Leftover-map graphic item coverage",', 1)
marker = '''  it.each([
    ["ko", "잔여 지도 그림 기준 포함 범위"],'''
if text.count(marker) != 1:
    raise SystemExit(f"i18n locale marker count={text.count(marker)}")
block = '''  it.each([
    ["ko", "잔여 지도 비교 불완전 기준"],
    ["zh", "残差地图比较不完整准则"],
    ["ja", "残差マップの比較不完全基準"],
    ["vi", "Tiêu chí không đầy đủ so sánh trên bản đồ phần dư"],
  ] as const)("formats leftover map comparison incomplete items label in %s", (locale, expected) => {
    setLocale(locale);
    expect(t("Leftover map comparison incomplete items")).toBe(expected);
  });

'''
p.write_text(text.replace(marker, block + marker, 1))

replace_once("pyproject.toml", 'version = "2.50.0"', 'version = "2.51.0"')
replace_once("lineageweave/__init__.py", '__version__ = "2.50.0"', '__version__ = "2.51.0"')
p = Path("frontend/package.json")
data = json.loads(p.read_text())
if data.get("version") != "2.50.0":
    raise SystemExit(f"frontend version drift={data.get('version')}")
data["version"] = "2.51.0"
p.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")

entry = '- Grouping comparison rows now show persisted leftover-map incomplete-item count through `leftoverMapIncompleteItemCount` (ADR 0294 / v2.51.0) only for fully caller-visible persisted groupings. Partial visibility remains omitted by the API; valid zero stays visible, and the UI never derives dropped criteria from scored-minus-used.\n\n'
replace_once("CHANGELOG.md", "## [Unreleased]\n\n### Added\n\n", "## [Unreleased]\n\n### Added\n\n" + entry)
Path("CHANGELOG.d/2.51.0-leftover-map-compare-incomplete-item.md").write_text("""## 2.51.0 — Grouping comparison incomplete-item coverage

- Show persisted leftover-map incomplete-item coverage on grouping comparison rows with a distinct accessible label (ADR 0294).
- Preserve API authorization: partial-visibility groupings have no full-population coverage object; the client does not reconstruct or recompute psychometrics.
- Persisted zero remains visible; invalid or contradictory counts are omitted.
""")
Path("docs/adr/0294-leftover-map-compare-incomplete-item.md").write_text("""# ADR 0294 — Grouping comparison incomplete-item coverage

**Decision status:** Proposed

## Problem
The grouping comparison strip omits the persisted incomplete-item count even though the full persisted grouping read model already carries authorization-filtered coverage.

## Decision
Render `leftoverMapIncompleteItemCount(row.leftover_map_coverage)` with the distinct accessible label `Leftover map comparison incomplete items`. Reuse the persisted-count validator. Do not derive the count from scored-minus-used, pair count, plotted criteria, or any other client-side proxy.

Only a full persisted grouping authorized by the API may carry the coverage object. Partial visibility must keep coverage absent; the frontend must not reconstruct a hidden full-population denominator or recompute psychometrics from the visible subset. Valid persisted zero remains visible. Missing, negative, non-integer, or contradictory counts fail closed.

This ADR remains Proposed while the PR is Draft. Accepted status requires current-head hosted tests, rendered keyboard/accessibility evidence, canonical eight-locale translation-ledger convergence, independent approval, and normal protected-branch merge.
""")
Path("tests/test_adr_0294_governance.py").write_text("""from pathlib import Path

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
""")
for path, block in {
    "AGENTS.md": "ADR 0294 keeps grouping-comparison incomplete-item coverage in the LineageWeave read-model boundary: consume only authorization-filtered persisted coverage for a full grouping, omit partial visibility, and never recompute psychometrics in the client.",
    "ARCHITECTURE.md": "ADR 0294 adds persisted incomplete-item coverage to grouping comparison presentation while the API remains the full-group visibility authority; the frontend formats only an admitted persisted count.",
    "CLAUDE.md": "ADR 0294 is the Proposed grouping-comparison incomplete-item presentation contract; preserve server-side full-group visibility gating and do not infer dropped criteria in the frontend.",
    "docs/product-technical-gap-baseline.md": "### 2026-09-07 — #825 current-parent reconstruction candidate\n\nExact parent `#824@499d653ed6e9206249e3f3a07518ad3fc01f14bd` lacks the grouping-comparison incomplete-item note while carrying authorization-filtered persisted coverage. ADR 0294 / v2.51.0 adds that buyer-visible read-model presentation and regression. Candidate evidence is not protected-main/release evidence; current-head browser/a11y, canonical eight-locale ledger consumption, independent review, and normal protected merge remain outstanding.",
}.items():
    p = Path(path)
    text = p.read_text()
    if block not in text:
        p.write_text(text.rstrip() + "\n\n" + block + "\n")
