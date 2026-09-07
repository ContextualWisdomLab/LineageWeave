from __future__ import annotations

import sys
from pathlib import Path


def replace_once(path: str, old: str, new: str, *, label: str) -> None:
    target = Path(path)
    text = target.read_text()
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{path}: {label} expected exactly one repair marker, found {count}")
    target.write_text(text.replace(old, new, 1))


def add_red() -> None:
    path = Path("frontend/src/App.test.tsx")
    text = path.read_text()
    marker = '''    const unexplainedSharePair = screen.getByRole("button", {
      name: /open leftover closest pair from comparison: public post.*leftover map comparison unexplained leftover share U²\\/R² 0\\.02/i,
    });
    expect(unexplainedSharePair).toHaveTextContent("U²/R² 0.02");'''
    addition = marker + '''
    const crossSharePair = screen.getByRole("button", {
      name: /open leftover closest pair from comparison: public post.*leftover map comparison cross share 2R̂U\\/R² 0\\.12/i,
    });
    expect(crossSharePair).toHaveTextContent("2R̂U/R² 0.12");
    expect(within(crossSharePair).getByText("2R̂U/R² 0.12")).toHaveAttribute(
      "aria-hidden",
      "true",
    );'''
    count = text.count(marker)
    if count != 1:
        raise SystemExit(f"current-parent App accessibility assertion marker count={count}")
    path.write_text(text.replace(marker, addition, 1))


def patch_app() -> None:
    path = Path("frontend/src/App.tsx")
    text = path.read_text()
    replacements = [
        (
            "cross-share import",
            '''import {
  formatLeftoverMapUnexplainedShare,
  LEFTOVER_MAP_COMPARE_UNEXPLAINED_SHARE_LABEL,
} from "./leftoverMapUnexplainedShare";
import {
  leftoverMapCompareAxisShare,''',
            '''import {
  formatLeftoverMapUnexplainedShare,
  LEFTOVER_MAP_COMPARE_UNEXPLAINED_SHARE_LABEL,
} from "./leftoverMapUnexplainedShare";
import {
  formatLeftoverMapCrossShare,
  LEFTOVER_MAP_COMPARE_CROSS_SHARE_LABEL,
} from "./leftoverMapCrossShare";
import {
  leftoverMapCompareAxisShare,''',
        ),
        (
            "cross-share value composition",
            '''                    const unexplainedShare = formatLeftoverMapUnexplainedShare(
                      pair.leftover_map_unexplained_share,
                    );
                    const pairAccessibleName = `Open leftover ${pair.pair_kind} pair from comparison: ${pair.post_title} · ${criterion}${''',
            '''                    const unexplainedShare = formatLeftoverMapUnexplainedShare(
                      pair.leftover_map_unexplained_share,
                    );
                    const crossShare = formatLeftoverMapCrossShare(pair.leftover_map_cross_share);
                    const pairAccessibleName = `Open leftover ${pair.pair_kind} pair from comparison: ${pair.post_title} · ${criterion}${''',
        ),
        (
            "cross-share accessible-name suffix",
            '''                    ${
                      unexplainedShare
                        ? ` · ${t(LEFTOVER_MAP_COMPARE_UNEXPLAINED_SHARE_LABEL)} ${unexplainedShare}`
                        : ""
                    }`;''',
            '''                    ${
                      unexplainedShare
                        ? ` · ${t(LEFTOVER_MAP_COMPARE_UNEXPLAINED_SHARE_LABEL)} ${unexplainedShare}`
                        : ""
                    }${
                      crossShare
                        ? ` · ${t(LEFTOVER_MAP_COMPARE_CROSS_SHARE_LABEL)} ${crossShare}`
                        : ""
                    }`;''',
        ),
        (
            "cross-share visual badge",
            '''                          {unexplainedShare ? (
                            <span className="post-badge" aria-hidden="true">
                              {unexplainedShare}
                            </span>
                          ) : null}
                        </button>''',
            '''                          {unexplainedShare ? (
                            <span className="post-badge" aria-hidden="true">
                              {unexplainedShare}
                            </span>
                          ) : null}
                          {crossShare ? (
                            <span className="post-badge" aria-hidden="true">
                              {crossShare}
                            </span>
                          ) : null}
                        </button>''',
        ),
    ]
    for label, old, new in replacements:
        count = text.count(old)
        if count != 1:
            raise SystemExit(f"frontend/src/App.tsx: {label} marker count={count}")
        text = text.replace(old, new, 1)
    path.write_text(text)


def apply_fix() -> None:
    patch_app()

    helper = Path("frontend/src/leftoverMapCrossShare.ts")
    helper_text = helper.read_text()
    old_helper = '''/** Leftover-map cross share ``x = 2 R̂ U / R²`` of raw residual. */

export const LEFTOVER_MAP_CROSS_SHARE_ACTION =
  "Two leftover-map axes leave identity remainder {value} of raw residual after IRT main effects. Open this post to read {criterion}.";

export function formatLeftoverMapCrossShare(
  value: number | null | undefined,
): string | null {
  if (value == null || !Number.isFinite(value)) {
    return null;
  }
  return `2R\\u0302U/R\\u00b2 ${value.toFixed(2)}`;
}
'''
    new_helper = '''/** Leftover-map cross share ``x = 2 R̂ U / R²`` of raw residual. */

export const LEFTOVER_MAP_CROSS_SHARE_ACTION =
  "Two leftover-map axes leave identity remainder {value} of raw residual after IRT main effects. Open this post to read {criterion}.";

export const LEFTOVER_MAP_COMPARE_CROSS_SHARE_LABEL =
  "Leftover map comparison cross share";

const LARGE_FIXED_TWO_DECIMAL = new Intl.NumberFormat("en-US", {
  useGrouping: false,
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
});

export function formatLeftoverMapCrossShare(
  value: number | null | undefined,
): string | null {
  if (value == null || !Number.isFinite(value)) {
    return null;
  }
  const formatted = Math.abs(value) >= 1e21 ? LARGE_FIXED_TWO_DECIMAL.format(value) : value.toFixed(2);
  return `2R\\u0302U/R\\u00b2 ${formatted}`;
}
'''
    if helper_text != old_helper:
        raise SystemExit("leftoverMapCrossShare.ts current-parent authority changed")
    helper.write_text(new_helper)

    helper_test = Path("frontend/src/leftoverMapCrossShare.test.ts")
    helper_test_text = helper_test.read_text()
    marker = '  it("omits the badge when leftover-map cross share is missing or non-finite", () => {'
    addition = '''  it("keeps large finite cross share in fixed two-decimal notation", () => {
    expect(formatLeftoverMapCrossShare(1e21)).toBe("2R\\u0302U/R\\u00b2 1000000000000000000000.00");
    expect(formatLeftoverMapCrossShare(-1e21)).toBe("2R\\u0302U/R\\u00b2 -1000000000000000000000.00");
  });

''' + marker
    count = helper_test_text.count(marker)
    if count != 1:
        raise SystemExit(f"cross-share edge-test marker count={count}")
    helper_test.write_text(helper_test_text.replace(marker, addition, 1))

    versions = {
        "pyproject.toml": ('version = "2.56.0"', 'version = "2.57.0"'),
        "lineageweave/__init__.py": ('__version__ = "2.56.0"', '__version__ = "2.57.0"'),
        "frontend/package.json": ('"version": "2.56.0"', '"version": "2.57.0"'),
    }
    for version_path, (old, new) in versions.items():
        replace_once(version_path, old, new, label="v2.57.0 version authority")

    Path("docs/adr/0371-leftover-map-compare-cross-share.md").write_text('''# ADR 0371 — Persisted leftover-map cross share in grouping-comparison pair actions

**Decision status:** Proposed

## Problem
Exact predecessor #830 (`b36b2534c9b3a63b66c56ae22ff3dcad40ae5c67`, ADR 0370 / v2.56.0) gives grouping-comparison pair buttons an explicit accessible name containing persisted reconstruction, explained-share, and unexplained-share evidence. Persisted leftover-map cross share `x = 2R̂U/R²` already exists in the authorized read model, but the comparison action omits it. Historical #831 displayed a separately labelled descendant badge, which leaves the actionable button name incomplete and can double-announce nested text.

## Constraints
- Consume only persisted `leftover_map_cross_share`; never derive `x` from `R̂`, `U`, `R`, distance, coordinates, rank, coverage, or any other UI-visible proxy.
- Missing or non-finite `x` omits only the cross-share suffix and badge. Finite zero and negative values remain explicit.
- The button accessible name carries the comparison label and formatted value. The duplicate visible badge is `aria-hidden` so it is not announced twice.
- Keep whole-population authorization and evidence boundaries inherited from the predecessor; never recompute hidden-population psychometric truth from visible members.
- Psychometric estimation remains owned by the released `fast-mlsirm` boundary. LineageWeave owns only this read-model/action composition.
- The comparison label is a translation key, not a new inline locale ledger. Canonical KO/EN/JA/ZH/VI/ES/DE/FR resources remain owned by the versioned translation-ledger path (#922/#929/#932).

## Decision
Use the existing persisted cross-share formatter in the grouping-comparison pair action. Append the formatted value to the button's explicit accessible name and render the same value as an `aria-hidden` visual badge. Retain finite values across the JavaScript fixed-point threshold by using non-exponential two-decimal formatting at `|x| >= 1e21`.

Historical ADR 0296 / v2.53.0 remains provenance only. This serialized successor allocates ADR 0371 / v2.57.0 and remains Proposed until the unchanged protected-main release is accepted.

## Verification
A current-parent role/name regression must fail before production changes because exact #830 lacks the cross-share suffix. GREEN requires the focused App/helper regressions, full frontend lint/test/build/Storybook, full PostgreSQL-backed Python suite, synchronized release versions and regenerated universal lock, plus a clean workflow-free product tree. Hosted security checks, current browser/responsive/keyboard/focus evidence, canonical eight-locale ledger consumption, and qualifying independent approval remain separate promotion gates.

## Evidence
Gabriel, K. R. (1971). The biplot graphic display of matrices with application to principal component analysis. *Biometrika, 58*(3), 453–467.

Jeon, M., Jin, I. H., Schweinberger, M., & Baugh, S. (2021). Mapping unobserved item–respondent interactions: A latent space item response model with interaction map. *Psychometrika, 86*(2), 378–403.
''')
    Path("CHANGELOG.d/2.57.0-leftover-map-compare-cross-share.md").write_text('''# v2.57.0 — grouping-comparison leftover-map cross share

Grouping-comparison pair actions now surface the persisted finite leftover-map cross share `x = 2R̂U/R²` in the action's accessible name and an `aria-hidden` visual badge under Proposed ADR 0371. Missing/non-finite values omit only this metric; finite zero and negative values remain explicit. The read model consumes persisted authority and does not recompute psychometric truth.
''')
    Path("tests/test_leftover_map_compare_cross_share_release_authority.py").write_text('''from __future__ import annotations

import json
import tomllib
from pathlib import Path

import lineageweave

ROOT = Path(__file__).resolve().parents[1]


def test_cross_share_release_authority_is_proposed_and_version_synchronized() -> None:
    project = tomllib.loads((ROOT / "pyproject.toml").read_text())
    frontend = json.loads((ROOT / "frontend/package.json").read_text())
    adr = (ROOT / "docs/adr/0371-leftover-map-compare-cross-share.md").read_text()
    assert project["project"]["version"] == "2.57.0"
    assert lineageweave.__version__ == "2.57.0"
    assert frontend["version"] == "2.57.0"
    assert "# ADR 0371" in adr
    assert "**Decision status:** Proposed" in adr
    assert "leftover_map_cross_share" in adr
''')


def main() -> None:
    if len(sys.argv) != 2 or sys.argv[1] not in {"red", "apply"}:
        raise SystemExit("usage: pr831_reconstruct.py red|apply")
    if sys.argv[1] == "red":
        add_red()
    else:
        apply_fix()


if __name__ == "__main__":
    main()
