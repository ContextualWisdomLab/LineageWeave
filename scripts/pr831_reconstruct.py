from __future__ import annotations

import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PARENT = "bebd77c03e5beae469f42361c20bccc80787ebb5"
WORKFLOW = Path(".github/workflows/pr831-reconstruct.yml")
SCRIPT = Path("scripts/pr831_reconstruct.py")


def run(*args: str, check: bool = True, cwd: Path = ROOT) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, cwd=cwd, check=check, text=True)


def replace_once(path: str, old: str, new: str) -> None:
    file = ROOT / path
    text = file.read_text(encoding="utf-8")
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{path}: expected one anchor, found {count}")
    file.write_text(text.replace(old, new, 1), encoding="utf-8")


def write(path: str, content: str) -> None:
    file = ROOT / path
    file.parent.mkdir(parents=True, exist_ok=True)
    file.write_text(content, encoding="utf-8")


def assert_staging_boundary() -> None:
    merge_base = subprocess.check_output(
        ["git", "merge-base", "HEAD", PARENT], cwd=ROOT, text=True
    ).strip()
    if merge_base != PARENT:
        raise SystemExit(f"staging branch drifted from exact parent: {merge_base}")
    changed = set(
        subprocess.check_output(
            ["git", "diff", "--name-only", f"{PARENT}..HEAD"], cwd=ROOT, text=True
        ).splitlines()
    )
    expected = {WORKFLOW.as_posix(), SCRIPT.as_posix()}
    if changed != expected:
        raise SystemExit(f"unexpected pre-repair staging delta: {sorted(changed)}")


def create_red_contracts() -> None:
    write(
        "backend/tests/test_report_ingestion_cross_share.py",
        '''"""Regression for persisted grouping-comparison cross-share transport."""

from __future__ import annotations

import asyncio
from decimal import Decimal

from backend.app import report_ingestion


class _ComparisonConnection:
    """Minimal asyncpg-compatible read boundary for one comparison row."""

    async def fetch(self, query: str, *_args: object) -> list[dict[str, object]]:
        if "from report_period_score" in query:
            return [{"grouping_kind": "thread_group", "grouping_key": "synthetic-thread", "mean_theta": 0.1, "post_count": 2, "link_method": "synthetic"}]
        if "from report_member_score" in query:
            return []
        if "from report_leftover_pair" in query:
            assert "lp.leftover_map_cross_share" in query, "leftover_map_cross_share is absent from comparison SELECT"
            common = {
                "grouping_kind": "thread_group",
                "grouping_key": "synthetic-thread",
                "post_id": "00000000-0000-0000-0000-000000000001",
                "post_title": "Synthetic comparison post",
                "criterion_code": "synthetic_criterion",
                "leftover_distance": 0.5,
                "leftover_residual": 0.4,
                "leftover_map_reconstruction": Decimal("0.25"),
                "leftover_map_unexplained_share": None,
                "visibility_code": "public",
                "corporate_entity_id": "00000000-0000-0000-0000-000000000002",
                "has_real_source_context": False,
            }
            return [
                {**common, "pair_kind": "closest", "leftover_map_cross_share": Decimal("0.12")},
                {**common, "pair_kind": "farthest", "leftover_map_cross_share": None},
            ]
        if "from report_leftover_map_coverage" in query or "from report_leftover_map_axis" in query:
            return []
        raise AssertionError(f"unexpected comparison query: {query}")


def test_fetch_period_comparison_transports_persisted_cross_share() -> None:
    """Persisted finite values reach the read model while SQL NULL remains unknown."""
    payload = asyncio.run(report_ingestion.fetch_period_comparison(_ComparisonConnection(), "2026-W02"))  # type: ignore[arg-type]
    pairs = payload[0]["leftover_pairs"]
    assert pairs[0]["leftover_map_cross_share"] == 0.12
    assert pairs[1]["leftover_map_cross_share"] is None
''',
    )
    write(
        "tests/test_leftover_map_compare_cross_share_accessibility_contract.py",
        '''"""Source-level contract for grouping-comparison cross-share evidence."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "frontend" / "src" / "App.tsx"
ADR = ROOT / "docs" / "adr" / "0372-leftover-map-compare-cross-share.md"


def test_comparison_cross_share_is_owned_by_actionable_pair_name() -> None:
    """The button must name persisted x while its visible duplicate stays silent."""
    source = APP.read_text(encoding="utf-8")
    assert 'import { formatLeftoverMapCrossShare } from "./leftoverMapCrossShare";' in source
    assert "const crossShare = formatLeftoverMapCrossShare(\n                      pair.leftover_map_cross_share,\n                    );" in source
    assert '${crossShare ? ` · ${crossShare}` : ""}' in source
    assert '<span className="post-badge" aria-hidden="true">\n                              {crossShare}\n                            </span>' in source
    assert "LEFTOVER_MAP_COMPARE_CROSS_SHARE_LABEL" not in source


def test_cross_share_decision_stays_proposed_and_current_parent_bound() -> None:
    """Reconstruction must not claim a release or stale historical ADR identity."""
    assert ADR.exists()
    text = ADR.read_text(encoding="utf-8")
    assert "**Decision status:** Proposed" in text
    assert "bebd77c03e5beae469f42361c20bccc80787ebb5" in text
    assert "No release version is allocated by this Draft" in text
''',
    )


def prove_red() -> None:
    backend = run(
        "uv",
        "run",
        "--frozen",
        "python",
        "-m",
        "pytest",
        "-q",
        "backend/tests/test_report_ingestion_cross_share.py",
        check=False,
    )
    ui = run(
        "uv",
        "run",
        "--frozen",
        "python",
        "-m",
        "pytest",
        "-q",
        "tests/test_leftover_map_compare_cross_share_accessibility_contract.py",
        check=False,
    )
    if backend.returncode == 0 or ui.returncode == 0:
        raise SystemExit(
            f"expected independent REDs before repair, got backend={backend.returncode}, ui={ui.returncode}"
        )


def apply_repair() -> None:
    replace_once(
        "backend/app/report_ingestion.py",
        '               lp.leftover_map_reconstruction, lp.leftover_map_unexplained_share,\n               p.post_title, p.visibility_code, p.corporate_entity_id,',
        '               lp.leftover_map_reconstruction, lp.leftover_map_unexplained_share,\n               lp.leftover_map_cross_share,\n               p.post_title, p.visibility_code, p.corporate_entity_id,',
    )
    replace_once(
        "backend/app/report_ingestion.py",
        '                        "leftover_map_unexplained_share": (\n                            None\n                            if pair["leftover_map_unexplained_share"] is None\n                            else float(pair["leftover_map_unexplained_share"])\n                        ),\n                        "visibility_code": pair["visibility_code"],',
        '                        "leftover_map_unexplained_share": (\n                            None\n                            if pair["leftover_map_unexplained_share"] is None\n                            else float(pair["leftover_map_unexplained_share"])\n                        ),\n                        "leftover_map_cross_share": (\n                            None\n                            if pair["leftover_map_cross_share"] is None\n                            else float(pair["leftover_map_cross_share"])\n                        ),\n                        "visibility_code": pair["visibility_code"],',
    )
    replace_once(
        "frontend/src/App.tsx",
        'import {\n  formatLeftoverMapUnexplainedShare,\n  LEFTOVER_MAP_COMPARE_UNEXPLAINED_SHARE_LABEL,\n} from "./leftoverMapUnexplainedShare";\nimport {\n  leftoverMapCompareAxisShare,',
        'import {\n  formatLeftoverMapUnexplainedShare,\n  LEFTOVER_MAP_COMPARE_UNEXPLAINED_SHARE_LABEL,\n} from "./leftoverMapUnexplainedShare";\nimport { formatLeftoverMapCrossShare } from "./leftoverMapCrossShare";\nimport {\n  leftoverMapCompareAxisShare,',
    )
    replace_once(
        "frontend/src/App.tsx",
        '                    const unexplainedShare = formatLeftoverMapUnexplainedShare(\n                      pair.leftover_map_unexplained_share,\n                    );\n                    const pairAccessibleName = `Open leftover ${pair.pair_kind} pair from comparison: ${pair.post_title} · ${criterion}${',
        '                    const unexplainedShare = formatLeftoverMapUnexplainedShare(\n                      pair.leftover_map_unexplained_share,\n                    );\n                    const crossShare = formatLeftoverMapCrossShare(\n                      pair.leftover_map_cross_share,\n                    );\n                    const pairAccessibleName = `Open leftover ${pair.pair_kind} pair from comparison: ${pair.post_title} · ${criterion}${',
    )
    replace_once(
        "frontend/src/App.tsx",
        '                    }${\n                      unexplainedShare\n                        ? ` · ${t(LEFTOVER_MAP_COMPARE_UNEXPLAINED_SHARE_LABEL)} ${unexplainedShare}`\n                        : ""\n                    }`;\n                    return (',
        '                    }${\n                      unexplainedShare\n                        ? ` · ${t(LEFTOVER_MAP_COMPARE_UNEXPLAINED_SHARE_LABEL)} ${unexplainedShare}`\n                        : ""\n                    }${crossShare ? ` · ${crossShare}` : ""}`;\n                    return (',
    )
    replace_once(
        "frontend/src/App.tsx",
        '                          {unexplainedShare ? (\n                            <span className="post-badge" aria-hidden="true">\n                              {unexplainedShare}\n                            </span>\n                          ) : null}\n                        </button>',
        '                          {unexplainedShare ? (\n                            <span className="post-badge" aria-hidden="true">\n                              {unexplainedShare}\n                            </span>\n                          ) : null}\n                          {crossShare ? (\n                            <span className="post-badge" aria-hidden="true">\n                              {crossShare}\n                            </span>\n                          ) : null}\n                        </button>',
    )
    replace_once(
        "frontend/src/App.test.tsx",
        '                    leftover_map_explained_share: 0.76,\n                    leftover_map_unexplained_share: 0.02,\n                  },',
        '                    leftover_map_explained_share: 0.76,\n                    leftover_map_unexplained_share: 0.02,\n                    leftover_map_cross_share: 0.12,\n                  },',
    )
    replace_once(
        "frontend/src/App.test.tsx",
        '    expect(\n      screen.getByRole("button", {\n        name: /open leftover closest pair from comparison: public post/i,\n      }),\n    ).toHaveTextContent("U²/R² 0.02");',
        '    expect(\n      screen.getByRole("button", {\n        name: /open leftover closest pair from comparison: public post/i,\n      }),\n    ).toHaveTextContent("U²/R² 0.02");\n    const publicPairButton = screen.getByRole("button", {\n      name: /open leftover closest pair from comparison: public post.*2R̂U\\/R² 0\\.12/i,\n    });\n    expect(publicPairButton).toHaveTextContent("2R̂U/R² 0.12");\n    expect(within(publicPairButton).getByText("2R̂U/R² 0.12")).toHaveAttribute("aria-hidden", "true");',
    )

    write(
        "docs/adr/0372-leftover-map-compare-cross-share.md",
        '''# ADR 0372 — Persisted leftover-map cross share in grouping comparison pair actions

**Decision status:** Proposed

## Problem
Exact #830 `bebd77c03e5beae469f42361c20bccc80787ebb5` preserves persisted leftover-map cross share `x = 2 R̂ U / R²` on the leftover-pair domain row and in the ordinary pair presentation, but its grouping-comparison query does not select or serialize that persisted field and its comparison action therefore cannot present the evidence. Historical #831 proved the buyer-visible intent on stale ancestry but used a generic author-provided badge label and stale ADR/release identities.

## Constraints
- Consume the persisted `leftover_map_cross_share`; never derive `x` from `R̂`, `U`, `R`, distance, coordinates, rank, coverage, counts, axis values, or another displayed share.
- SQL NULL, missing, and non-finite presentation values omit only this metric. Persisted finite zero and finite negative values remain explicit and unclamped.
- Keep the existing complete-visible-grouping authorization boundary. No hidden-population psychometric truth is reconstructed from a caller-visible subset.
- The actionable pair button must expose the same finite cross-share text the buyer sees. The duplicate visible badge is `aria-hidden` so it is not announced twice.
- Reuse `formatLeftoverMapCrossShare`; do not add a comparison-specific author-name token or a competing inline translation ledger. Canonical KO/EN/JA/ZH/VI/ES/DE/FR resources remain owned by #929/#932.
- Psychometric estimation/validation remains outside this UI/read-model composition decision.

## Alternatives and decision
Omitting `x` discards persisted evidence. Recomputing it would move measurement authority into the consumer. A child badge with a generic `aria-label` can override useful visible mathematical text and duplicate announcements. Therefore select and serialize the persisted field, format it through the existing cross-share formatter, append that exact visible text to the actionable pair accessible name, and hide only the duplicate visual badge from accessibility APIs.

No release version is allocated by this Draft. Historical ADR 0296 / v2.53.0 is provenance only; release identity is assigned only from the then-current protected release authority after the serialized stack and acceptance gates converge.

## Verification
The current-parent transport regression must RED while the comparison SELECT omits `lp.leftover_map_cross_share`, then GREEN after only SELECT/serialization repair. The UI source contract and rendered App integration must RED while the comparison action omits the metric, then GREEN only when the button name and `aria-hidden` duplicate badge consume the same formatted persisted value without `LEFTOVER_MAP_COMPARE_CROSS_SHARE_LABEL`. Full PostgreSQL-backed tests, frontend lint/tests/build/Storybook, hosted security gates, current rendered responsive/pointer/touch/keyboard/focus/a11y evidence, and qualifying independent approval remain separate exact-head acceptance gates.

## Evidence
Gabriel, K. R. (1971). The biplot graphic display of matrices with application to principal component analysis. *Biometrika, 58*(3), 453–467.

Jeon, M., Jin, I. H., Schweinberger, M., & Baugh, S. (2021). Mapping unobserved item–respondent interactions: A latent space item response model with interaction map. *Psychometrika, 86*(2), 378–403.
''',
    )
    replace_once(
        "CHANGELOG.md",
        "## [Unreleased]\n\n### Added\n\n",
        "## [Unreleased]\n\n### Added\n\n- Grouping comparison leftover-pair actions now transport and show persisted finite cross share `2R̂U/R²` under Proposed ADR 0372. The same formatted persisted value is included in the actionable button name while the duplicate visible badge is accessibility-hidden; missing/non-finite values omit only this metric, and zero/finite-negative values remain explicit without client-side derivation or clamping.\n\n",
    )
    replace_once(
        "docs/product-technical-gap-baseline.md",
        "# Product & Technical Gap Baseline\n\n",
        "> Current serialized reconstruction (2026-09-11): #831 is rebuilt from exact #830 `bebd77c03e5beae469f42361c20bccc80787ebb5` under Proposed ADR 0372. The grouping-comparison read model transports persisted `leftover_map_cross_share` and the pair action presents the existing formatted `2R̂U/R²` value in its accessible name while the duplicate visual badge is accessibility-hidden. Missing/non-finite values omit only this metric; persisted finite zero/negative values remain explicit. No comparison-specific translation ledger or client-side psychometric derivation is introduced; #929/#932 remain canonical translation authority. Historical ADR0296/v2.53.0 is provenance only, and this Draft allocates no release version.\n\n# Product & Technical Gap Baseline\n\n",
    )
    replace_once(
        "ARCHITECTURE.md",
        "ADR 0293 captions grouping-comparison persisted incomplete-post count only for a fully caller-visible persisted grouping; partial visibility omits the aggregate rather than disclosing or recomputing a hidden-population count.\n",
        "ADR 0293 captions grouping-comparison persisted incomplete-post count only for a fully caller-visible persisted grouping; partial visibility omits the aggregate rather than disclosing or recomputing a hidden-population count.\nADR 0372 transports persisted leftover-map cross share `x = 2 R̂ U / R²` through the authorized grouping-comparison read model and exposes the existing formatted value on the actionable leftover-pair name; the duplicate visible badge is accessibility-hidden and the consumer never recomputes psychometric truth.\n",
    )


def verify_green() -> None:
    run(
        "uv",
        "run",
        "--frozen",
        "python",
        "-m",
        "pytest",
        "-q",
        "backend/tests/test_report_ingestion_cross_share.py",
        "tests/test_leftover_map_compare_cross_share_accessibility_contract.py",
    )
    run("uv", "run", "--frozen", "python", "-m", "pytest", "-q")
    run("pnpm", "run", "lint", cwd=ROOT / "frontend")
    run("pnpm", "run", "test", cwd=ROOT / "frontend")
    run("pnpm", "run", "build", cwd=ROOT / "frontend")
    run("pnpm", "run", "build-storybook", cwd=ROOT / "frontend")


def publish_candidate() -> None:
    (ROOT / WORKFLOW).unlink()
    (ROOT / SCRIPT).unlink()
    expected = {
        "ARCHITECTURE.md",
        "CHANGELOG.md",
        "backend/app/report_ingestion.py",
        "backend/tests/test_report_ingestion_cross_share.py",
        "docs/adr/0372-leftover-map-compare-cross-share.md",
        "docs/product-technical-gap-baseline.md",
        "frontend/src/App.test.tsx",
        "frontend/src/App.tsx",
        "tests/test_leftover_map_compare_cross_share_accessibility_contract.py",
        WORKFLOW.as_posix(),
        SCRIPT.as_posix(),
    }
    changed = set(
        subprocess.check_output(["git", "status", "--porcelain=v1"], cwd=ROOT, text=True)
        .strip()
        .splitlines()
    )
    paths = {line[3:] for line in changed if line}
    if paths != expected:
        raise SystemExit(f"unexpected candidate delta: {sorted(paths)}")
    run("git", "config", "user.name", "github-actions[bot]")
    run(
        "git",
        "config",
        "user.email",
        "41898282+github-actions[bot]@users.noreply.github.com",
    )
    run("git", "add", "-A")
    run(
        "git",
        "commit",
        "-m",
        "feat(reports): reconstruct grouping comparison cross share [skip ci]",
    )
    if subprocess.check_output(["git", "status", "--porcelain"], cwd=ROOT, text=True):
        raise SystemExit("candidate tree is dirty after commit")
    run("git", "push", "origin", "HEAD:repair/pr831-cross-share-r11-01")


def main() -> None:
    assert_staging_boundary()
    create_red_contracts()
    prove_red()
    apply_repair()
    verify_green()
    publish_candidate()


if __name__ == "__main__":
    main()
