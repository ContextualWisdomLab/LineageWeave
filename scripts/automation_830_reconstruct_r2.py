#!/usr/bin/env python3
"""Temporary #830 reconstruction driver for exact #829.

This file exists only on the reconstruction branch and is removed before a clean
staging commit is published.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

RED_TEST = Path("frontend/src/leftoverMapCompareAxis.reconstruction-red.test.ts")


def replace_once(path: str, old: str, new: str) -> None:
    p = Path(path)
    text = p.read_text()
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{path}: expected exactly one replacement target, found {count}")
    p.write_text(text.replace(old, new, 1))


def write_red() -> None:
    RED_TEST.write_text(
        '''import { expect, it } from "vitest";\n'''
        '''import { leftoverMapCompareAxisSingular } from "./leftoverMapCompareAxis";\n\n'''
        '''it("exposes persisted grouping-comparison singular value on current parent", () => {\n'''
        '''  expect(leftoverMapCompareAxisSingular({ axis_index: 1, leftover_singular_value: 1.84 })).toEqual({\n'''
        '''    axis: 1,\n'''
        '''    value: "1.84",\n'''
        '''  });\n'''
        '''});\n'''
    )


def cleanup_red() -> None:
    RED_TEST.unlink(missing_ok=True)


def apply_fix() -> None:
    cleanup_red()
    Path("frontend/src/leftoverMapCompareAxis.ts").write_text(
        '''/** Caption persisted leftover-map axis share and singular values on the grouping comparison strip (ADR 0367 / ADR 0370). */\n\n'''
        '''import type { LeftoverMapAxis } from "./api";\n\n'''
        '''export const LEFTOVER_MAP_COMPARE_AXIS_SHARE_LABEL = "Leftover map comparison axis share";\n'''
        '''export const LEFTOVER_MAP_COMPARE_AXIS_SHARE = "leftover map comparison axis {axis} {share}%";\n'''
        '''export const LEFTOVER_MAP_LIST_AXIS_SHARE = "leftover axis {axis} {share}%";\n'''
        '''export const LEFTOVER_MAP_PLOT_AXIS_SHARE = "leftover-map axis {axis} ({share}%)";\n\n'''
        '''export const LEFTOVER_MAP_COMPARE_AXIS_SINGULAR_LABEL = "Leftover map comparison axis singular";\n'''
        '''export const LEFTOVER_MAP_COMPARE_AXIS_SINGULAR = "leftover map comparison axis {axis} σ {value}";\n\n'''
        '''export type LeftoverMapCompareAxisShare = {\n  axis: number;\n  share: string;\n};\n\n'''
        '''export type LeftoverMapCompareAxisSingular = {\n  axis: number;\n  value: string;\n};\n\n'''
        '''export function leftoverMapCompareAxisShare(\n'''
        '''  axis: Pick<LeftoverMapAxis, "axis_index" | "leftover_share"> | null | undefined,\n'''
        '''): LeftoverMapCompareAxisShare | null {\n'''
        '''  if (axis == null) return null;\n'''
        '''  if (!Number.isInteger(axis.axis_index) || axis.axis_index < 1) return null;\n'''
        '''  if (axis.leftover_share == null || !Number.isFinite(axis.leftover_share)) return null;\n'''
        '''  return { axis: axis.axis_index, share: (axis.leftover_share * 100).toFixed(0) };\n'''
        '''}\n\n'''
        '''export function leftoverMapCompareAxisSingular(\n'''
        '''  axis: Pick<LeftoverMapAxis, "axis_index" | "leftover_singular_value"> | null | undefined,\n'''
        '''): LeftoverMapCompareAxisSingular | null {\n'''
        '''  if (axis == null) return null;\n'''
        '''  if (!Number.isInteger(axis.axis_index) || axis.axis_index < 1) return null;\n'''
        '''  if (\n'''
        '''    axis.leftover_singular_value == null ||\n'''
        '''    !Number.isFinite(axis.leftover_singular_value) ||\n'''
        '''    axis.leftover_singular_value < 0\n'''
        '''  ) {\n'''
        '''    return null;\n'''
        '''  }\n'''
        '''  return { axis: axis.axis_index, value: axis.leftover_singular_value.toFixed(2) };\n'''
        '''}\n'''
    )

    replace_once(
        "frontend/src/leftoverMapCompareAxis.test.ts",
        '''  leftoverMapCompareAxisShare,\n  LEFTOVER_MAP_COMPARE_AXIS_SHARE,\n  LEFTOVER_MAP_COMPARE_AXIS_SHARE_LABEL,\n  LEFTOVER_MAP_LIST_AXIS_SHARE,\n  LEFTOVER_MAP_PLOT_AXIS_SHARE,\n''',
        '''  leftoverMapCompareAxisShare,\n  leftoverMapCompareAxisSingular,\n  LEFTOVER_MAP_COMPARE_AXIS_SHARE,\n  LEFTOVER_MAP_COMPARE_AXIS_SHARE_LABEL,\n  LEFTOVER_MAP_COMPARE_AXIS_SINGULAR,\n  LEFTOVER_MAP_COMPARE_AXIS_SINGULAR_LABEL,\n  LEFTOVER_MAP_LIST_AXIS_SHARE,\n  LEFTOVER_MAP_PLOT_AXIS_SHARE,\n''',
    )
    test_path = Path("frontend/src/leftoverMapCompareAxis.test.ts")
    test_path.write_text(
        test_path.read_text()
        + '''\n\ndescribe("leftoverMapCompareAxisSingular", () => {\n'''
        + '''  it("names persisted finite non-negative singular values, including zero", () => {\n'''
        + '''    expect(leftoverMapCompareAxisSingular({ axis_index: 1, leftover_singular_value: 1.84 })).toEqual({ axis: 1, value: "1.84" });\n'''
        + '''    expect(leftoverMapCompareAxisSingular({ axis_index: 2, leftover_singular_value: 0.86 })).toEqual({ axis: 2, value: "0.86" });\n'''
        + '''    expect(leftoverMapCompareAxisSingular({ axis_index: 1, leftover_singular_value: 0 })).toEqual({ axis: 1, value: "0.00" });\n'''
        + '''  });\n\n'''
        + '''  it("omits missing, invalid-axis, non-finite, and negative singular values", () => {\n'''
        + '''    expect(leftoverMapCompareAxisSingular(null)).toBeNull();\n'''
        + '''    expect(leftoverMapCompareAxisSingular(undefined)).toBeNull();\n'''
        + '''    expect(leftoverMapCompareAxisSingular({ axis_index: 0, leftover_singular_value: 1.84 })).toBeNull();\n'''
        + '''    expect(leftoverMapCompareAxisSingular({ axis_index: 1 })).toBeNull();\n'''
        + '''    expect(leftoverMapCompareAxisSingular({ axis_index: 1, leftover_singular_value: Number.NaN })).toBeNull();\n'''
        + '''    expect(leftoverMapCompareAxisSingular({ axis_index: 1, leftover_singular_value: Number.POSITIVE_INFINITY })).toBeNull();\n'''
        + '''    expect(leftoverMapCompareAxisSingular({ axis_index: 1, leftover_singular_value: -0.01 })).toBeNull();\n'''
        + '''  });\n\n'''
        + '''  it("keeps singular presentation distinct from axis share", () => {\n'''
        + '''    expect(LEFTOVER_MAP_COMPARE_AXIS_SINGULAR_LABEL).toBe("Leftover map comparison axis singular");\n'''
        + '''    expect(LEFTOVER_MAP_COMPARE_AXIS_SINGULAR_LABEL).not.toBe(LEFTOVER_MAP_COMPARE_AXIS_SHARE_LABEL);\n'''
        + '''    expect(LEFTOVER_MAP_COMPARE_AXIS_SINGULAR).toBe("leftover map comparison axis {axis} σ {value}");\n'''
        + '''    expect(leftoverMapCompareAxisSingular({ axis_index: 1, leftover_singular_value: 1.84 })).not.toEqual({ axis: 1, value: "82" });\n'''
        + '''  });\n'''
        + '''});\n'''
    )

    replace_once(
        "frontend/src/App.tsx",
        'import { Component, lazy, Suspense, useCallback, useEffect, useEffectEvent, useRef, useState, type ReactNode } from "react";',
        'import { Component, Fragment, lazy, Suspense, useCallback, useEffect, useEffectEvent, useRef, useState, type ReactNode } from "react";',
    )
    replace_once(
        "frontend/src/App.tsx",
        '''import {\n  leftoverMapCompareAxisShare,\n  LEFTOVER_MAP_COMPARE_AXIS_SHARE,\n  LEFTOVER_MAP_COMPARE_AXIS_SHARE_LABEL,\n} from "./leftoverMapCompareAxis";''',
        '''import {\n  leftoverMapCompareAxisShare,\n  leftoverMapCompareAxisSingular,\n  LEFTOVER_MAP_COMPARE_AXIS_SHARE,\n  LEFTOVER_MAP_COMPARE_AXIS_SHARE_LABEL,\n  LEFTOVER_MAP_COMPARE_AXIS_SINGULAR,\n  LEFTOVER_MAP_COMPARE_AXIS_SINGULAR_LABEL,\n} from "./leftoverMapCompareAxis";''',
    )
    replace_once(
        "frontend/src/App.tsx",
        '''              {row.leftover_map_axes?.map((axis) => {\n                const comparisonAxisShare = leftoverMapCompareAxisShare(axis);\n                if (comparisonAxisShare === null) {\n                  return null;\n                }\n                return (\n                  <span\n                    key={axis.axis_index}\n                    className="post-badge"\n                    aria-label={t(LEFTOVER_MAP_COMPARE_AXIS_SHARE_LABEL)}\n                  >\n                    {tf(LEFTOVER_MAP_COMPARE_AXIS_SHARE, comparisonAxisShare)}\n                  </span>\n                );\n              })}''',
        '''              {row.leftover_map_axes?.map((axis) => {\n                const comparisonAxisShare = leftoverMapCompareAxisShare(axis);\n                const comparisonAxisSingular = leftoverMapCompareAxisSingular(axis);\n                if (comparisonAxisShare === null && comparisonAxisSingular === null) {\n                  return null;\n                }\n                return (\n                  <Fragment key={axis.axis_index}>\n                    {comparisonAxisShare !== null ? (\n                      <span\n                        className="post-badge"\n                        aria-label={t(LEFTOVER_MAP_COMPARE_AXIS_SHARE_LABEL)}\n                      >\n                        {tf(LEFTOVER_MAP_COMPARE_AXIS_SHARE, comparisonAxisShare)}\n                      </span>\n                    ) : null}\n                    {comparisonAxisSingular !== null ? (\n                      <span\n                        className="post-badge"\n                        aria-label={t(LEFTOVER_MAP_COMPARE_AXIS_SINGULAR_LABEL)}\n                      >\n                        {tf(LEFTOVER_MAP_COMPARE_AXIS_SINGULAR, comparisonAxisSingular)}\n                      </span>\n                    ) : null}\n                  </Fragment>\n                );\n              })}''',
    )
    replace_once(
        "frontend/src/App.test.tsx",
        '''    expect(\n      within(screen.getByLabelText("Grouping comparison")).queryByText(/σ 1\\.84/),\n    ).not.toBeInTheDocument();''',
        '''    expect(\n      within(screen.getByLabelText("Grouping comparison")).getAllByLabelText(\n        "Leftover map comparison axis singular",\n      ),\n    ).toHaveLength(4);\n    expect(\n      within(screen.getByLabelText("Grouping comparison")).getAllByLabelText(\n        "Leftover map comparison axis singular",\n      )[0],\n    ).toHaveTextContent("leftover map comparison axis 1 σ 0.00");\n    expect(\n      within(screen.getByLabelText("Grouping comparison")).getByText(\n        "leftover map comparison axis 1 σ 1.84",\n      ),\n    ).toBeInTheDocument();\n    expect(\n      within(screen.getByLabelText("Grouping comparison")).getByText(\n        "leftover map comparison axis 2 σ 0.86",\n      ),\n    ).toBeInTheDocument();''',
    )
    replace_once(
        "backend/tests/test_api.py",
        '''    assert leftover_compare_axes[0]["leftover_share"] != leftover_compare_axes[0][\n        "leftover_singular_value"\n    ] or leftover_compare_axes[0]["leftover_share"] in {0, 1}\n''',
        '''    assert leftover_compare_axes[0]["leftover_share"] != leftover_compare_axes[0][\n        "leftover_singular_value"\n    ] or leftover_compare_axes[0]["leftover_share"] in {0, 1}\n    assert all(\n        isinstance(axis["leftover_singular_value"], (int, float)) for axis in leftover_compare_axes\n    )\n    assert all(\n        axis["leftover_singular_value"] == axis["leftover_singular_value"]\n        and axis["leftover_singular_value"] >= 0\n        for axis in leftover_compare_axes\n    )\n''',
    )

    replace_once("pyproject.toml", 'version = "2.55.0"', 'version = "2.56.0"')
    replace_once("lineageweave/__init__.py", '__version__ = "2.55.0"', '__version__ = "2.56.0"')
    replace_once("frontend/package.json", '"version": "2.55.0"', '"version": "2.56.0"')

    Path("docs/adr/0370-leftover-map-compare-axis-singular.md").write_text(
        '''# ADR 0370 — Name persisted leftover-map singular values on grouping comparison axes\n\n'''
        '''**Decision status:** Proposed  \n**Date:** 2026-09-07\n\n'''
        '''## Context\n\nADR 0367 exposes persisted grouping-comparison axis share only under the read-model authorization boundary. The same report axis already carries persisted `leftover_singular_value`, but the current grouping comparison strip does not name that Gabriel scale. Axis share and singular value are different persisted quantities; reconstructing one from the other or from visible pairs, markers, counts, rank, coverage, or a caller-visible subset would manufacture psychometric truth.\n\nThe eight-locale resource system is owned by the PostgreSQL translation-ledger path (#922/#929/#932). This increment must not create or extend a competing source-code translation store.\n\n'''
        '''## Decision\n\nLineageWeave may present `leftover_singular_value` on each authorized grouping-comparison axis through `leftoverMapCompareAxisSingular` only when the persisted value is finite and non-negative and `axis_index` is a positive integer. Persisted zero is rendered as `0.00`. Missing, non-finite, negative, or invalid-axis data omits only the singular badge; axis-share presentation remains independent.\n\nThe buyer-facing caption is `leftover map comparison axis {axis} σ {value}` with the distinct accessible name `Leftover map comparison axis singular`. No SQL migration, local psychometric calculation, cross-service SQL, provider call, or new translation store is introduced. Partial-visibility grouping aggregates continue to fail closed under the existing authorization contract; the client never recomputes a hidden denominator.\n\n'''
        '''## Alternatives\n\n- **Derive `σ` from axis share:** rejected because share loses the residual scale and cannot identify `σ` without additional persisted information.\n- **Replay historical #830 wholesale:** rejected because five cumulative files conflict with the current serialized parent and would overwrite later authority.\n- **Add strings to legacy `i18n.ts`:** rejected because the canonical database-backed translation ledger is the product translation authority.\n\n'''
        '''## Consequences and verification\n\nThe grouping strip can name both share and singular value independently. Formatter tests cover positive, zero, missing, non-finite, negative, and invalid-axis values; authenticated report UI tests verify independent badges; PostgreSQL-backed API regression verifies the serialized singular values are finite and non-negative. This ADR remains Proposed while #830 is Draft.\n\n'''
        '''## References\n\nGabriel, K. R. (1971). The biplot graphic display of matrices with application to principal component analysis. *Biometrika, 58*(3), 453–467. https://doi.org/10.1093/biomet/58.3.453\n\nJeon, M., Jin, I. H., Schweinberger, M., & Baugh, S. (2021). Mapping unobserved item–respondent interactions: A latent space item response model with interaction map. *Psychometrika, 86*(2), 378–403. https://doi.org/10.1007/s11336-021-09762-5\n'''
    )
    Path("CHANGELOG.d/2.56.0-leftover-map-compare-axis-singular.md").write_text(
        '''### Added\n\n- Grouping-comparison leftover-map axes now name the persisted finite, non-negative singular value independently of axis share, including persisted zero; invalid or unavailable singular evidence fails closed without manufacturing a value.\n'''
    )


def verify_diff() -> None:
    cleanup_red()
    allowed = {
        "backend/tests/test_api.py",
        "CHANGELOG.d/2.56.0-leftover-map-compare-axis-singular.md",
        "docs/adr/0370-leftover-map-compare-axis-singular.md",
        "frontend/package.json",
        "frontend/src/App.test.tsx",
        "frontend/src/App.tsx",
        "frontend/src/leftoverMapCompareAxis.test.ts",
        "frontend/src/leftoverMapCompareAxis.ts",
        "lineageweave/__init__.py",
        "pyproject.toml",
        "uv.lock",
    }
    names = subprocess.check_output(["git", "diff", "--name-only", "HEAD~2"], text=True).splitlines()
    transient = {
        ".github/workflows/automation-830-reconstruct-r2.yml",
        "scripts/automation_830_reconstruct_r2.py",
    }
    unexpected = set(names) - allowed - transient
    if unexpected:
        raise SystemExit(f"unexpected product paths: {sorted(unexpected)}")


COMMANDS = {
    "red": write_red,
    "cleanup-red": cleanup_red,
    "apply": apply_fix,
    "verify": verify_diff,
}

if __name__ == "__main__":
    try:
        command = sys.argv[1]
    except IndexError as exc:
        raise SystemExit(f"usage: {Path(sys.argv[0]).name} <{'|'.join(COMMANDS)}>") from exc
    try:
        fn = COMMANDS[command]
    except KeyError as exc:
        raise SystemExit(f"unknown command: {command}") from exc
    fn()
