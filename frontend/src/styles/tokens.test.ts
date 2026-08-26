/// <reference types="node" />
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";

const here = dirname(fileURLToPath(import.meta.url));
const tokensCss = readFileSync(join(here, "tokens.css"), "utf-8");
const appCss = readFileSync(join(here, "..", "App.css"), "utf-8");
const publicClaimCss = readFileSync(
  join(here, "..", "components", "PublicClaimVerification.css"),
  "utf-8",
);

const [lightBlock, darkBlock] = tokensCss.split("@media (prefers-color-scheme: dark)");

const BADGE_AND_ACCENT_TOKENS = [
  "--color-border-subtle",
  "--color-accent-info",
  "--color-accent-info-background",
  "--color-accent-secondary",
  "--color-accent-secondary-background",
  "--badge-actor-person-bg",
  "--badge-actor-person-text",
  "--badge-actor-organization-bg",
  "--badge-actor-organization-text",
  "--badge-actor-team-bg",
  "--badge-actor-team-text",
  "--badge-status-pending-bg",
  "--badge-status-pending-text",
  "--badge-status-success-bg",
  "--badge-status-success-text",
  "--badge-status-danger-bg",
  "--badge-status-danger-text",
  "--badge-status-evidence-bg",
  "--badge-status-evidence-text",
  "--badge-status-inference-bg",
  "--badge-status-inference-text",
  "--badge-status-prediction-bg",
  "--badge-status-prediction-text",
];

const ONTOLOGY_NODE_TOKENS = [
  "--ontology-node-post-fill",
  "--ontology-node-person-fill",
  "--ontology-node-organization-fill",
  "--ontology-node-team-fill",
  "--ontology-node-project-fill",
  "--ontology-node-generic-fill",
];

// Colors this file's dark-mode block replaced -- a regression here would
// silently make dark mode as bright as light mode again (ADR 0099).
const RETIRED_LIGHT_ONLY_HEX = [
  "#2563eb",
  "#7c3aed",
  "#e8eaf6",
  "#303f9f",
  "#fff3e0",
  "#9a3412",
  "#e0f2f1",
  "#00695c",
  "#d4edda",
  "#155724",
  "#f8d7da",
  "#721c24",
];

// WCAG 2.x relative luminance / contrast ratio (SC 1.4.3).
function relativeLuminance(hex: string): number {
  const normalized = hex.length === 4
    ? `#${[...hex.slice(1)].map((digit) => `${digit}${digit}`).join("")}`
    : hex;
  const rgb = [1, 3, 5].map((i) => parseInt(normalized.slice(i, i + 2), 16) / 255);
  const [r, g, b] = rgb.map((c) => (c <= 0.03928 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4));
  return 0.2126 * r + 0.7152 * g + 0.0722 * b;
}

function contrastRatio(hexA: string, hexB: string): number {
  const lA = relativeLuminance(hexA);
  const lB = relativeLuminance(hexB);
  const [lighter, darker] = lA > lB ? [lA, lB] : [lB, lA];
  return (lighter + 0.05) / (darker + 0.05);
}

function escapeRegExp(value: string): string {
  return value.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

function readToken(block: string, token: string): string {
  // Safe regex: `token` is always a hardcoded CSS custom-property name
  // literal passed by the call sites below (e.g. "--color-footer-bg"), and
  // escapeRegExp() neutralizes any regex metacharacters before
  // interpolation, so no caller-controlled input reaches RegExp unescaped.
  const match = block.match(new RegExp(`${escapeRegExp(token)}:\\s*(#[0-9a-fA-F]{6}|#[0-9a-fA-F]{3})(?![0-9a-fA-F])`)); // nosemgrep: javascript.lang.security.audit.detect-non-literal-regexp.detect-non-literal-regexp
  if (!match) throw new Error(`${token} not found as a hex value`);
  return match[1];
}

// Secondary <details>/<summary> disclosure toggles (advanced tools,
// evidence-extraction actions, related-post/hint expanders) must meet the
// same --size-control-min touch target as primary controls like
// .language-switcher select and .lineage-entity-picker select (ADR-less
// touch_interaction gap fix).
const DISCLOSURE_TOGGLE_SELECTORS = [
  ".advanced-review-tools summary",
  ".semantic-provenance summary",
  ".operator-action-tools summary",
  ".keyman-source-context summary",
  ".hint-disclosure summary",
];

describe("design tokens", () => {
  it("keeps footer text at or above the WCAG AA 4.5:1 contrast minimum (SC 1.4.3)", () => {
    const footerBg = readToken(lightBlock, "--color-footer-bg");
    const footerText = readToken(lightBlock, "--color-footer-text");
    expect(contrastRatio(footerBg, footerText)).toBeGreaterThanOrEqual(4.5);
  });


  it("defines every badge/accent token in both the light and dark blocks", () => {
    for (const token of BADGE_AND_ACCENT_TOKENS) {
      expect(lightBlock, `${token} missing from the light :root block`).toContain(`${token}:`);
      expect(darkBlock, `${token} missing from the dark prefers-color-scheme block`).toContain(
        `${token}:`,
      );
    }
  });

  it("does not repeat the retired inline hex colors those tokens replaced", () => {
    for (const hex of RETIRED_LIGHT_ONLY_HEX) {
      expect(appCss.toLowerCase(), `${hex} should be a token reference, not inline`).not.toContain(
        hex.toLowerCase(),
      );
    }
  });

  it("keeps App.css's badge/accent declarations pointed at var(), not literals", () => {
    for (const token of BADGE_AND_ACCENT_TOKENS) {
      expect(appCss, `App.css never references var(${token})`).toContain(`var(${token})`);
    }
  });

  it("defines and consumes ontology node fills in both color schemes", () => {
    for (const token of ONTOLOGY_NODE_TOKENS) {
      expect(lightBlock, `${token} missing from the light :root block`).toContain(`${token}:`);
      expect(darkBlock, `${token} missing from the dark prefers-color-scheme block`).toContain(
        `${token}:`,
      );
      expect(appCss, `App.css never references var(${token})`).toContain(`var(${token})`);
    }
  });

  it("keeps ontology labels and their halo at WCAG AA contrast in both color schemes", () => {
    for (const block of [lightBlock, darkBlock]) {
      const background = readToken(block, "--color-background");
      for (const token of ["--color-text-heading", "--color-text"]) {
        expect(contrastRatio(readToken(block, token), background), `${token} label contrast`)
          .toBeGreaterThanOrEqual(4.5);
      }
    }
  });

  it("does not dim .post-meta with opacity -- it fails WCAG AA in both themes and carries role=\"status\" next-action text", () => {
    const match = appCss.match(/\.post-meta\s*\{([^}]*)\}/);
    expect(match, ".post-meta rule not found in App.css").not.toBeNull();
    expect(match?.[1] ?? "").not.toMatch(/opacity\s*:/);
    // Dropping the dimming must not also drop the size: the meta line
    // stays visually secondary through font-size, not through opacity.
    expect(match?.[1] ?? "").toContain("font-size: 0.85rem");
  });

  it("gives .citation-chip a real 24px minimum touch target", () => {
    const citationChipBlock = appCss.match(/\.citation-chip\s*\{[^}]*\}/)?.[0] ?? "";
    expect(citationChipBlock, ".citation-chip rule not found in App.css").not.toBe("");
    expect(citationChipBlock).toContain("min-height: var(--size-control-min)");
    // The chip is a bare <button>; without flex centering its text sits at
    // the top of the box once min-height grows past the line height.
    expect(citationChipBlock).toContain("display: inline-flex");
    expect(citationChipBlock).toContain("align-items: center");
  });

  it("gives Dashboard evidence links the shared minimum touch target", () => {
    const rule = appCss.match(/\.btn-link\s*\{[^}]*\}/)?.[0] ?? "";
    expect(rule, ".btn-link rule not found in App.css").not.toBe("");
    expect(rule).toContain("min-height: var(--size-control-min)");
    expect(rule).toContain("display: inline-flex");
    expect(rule).toContain("align-items: center");
  });
});

describe("secondary disclosure toggle touch targets", () => {
  it("declares every hint/tools <summary> selector", () => {
    for (const selector of DISCLOSURE_TOGGLE_SELECTORS) {
      expect(appCss, `${selector} missing from App.css`).toContain(selector);
    }
  });

  it("sizes those selectors with the shared --size-control-min token, not a bespoke value", () => {
    const ruleStart = appCss.indexOf(DISCLOSURE_TOGGLE_SELECTORS[0]);
    expect(ruleStart, `${DISCLOSURE_TOGGLE_SELECTORS[0]} not found in App.css`).toBeGreaterThanOrEqual(0);
    const ruleEnd = appCss.indexOf("}", ruleStart);
    const rule = appCss.slice(ruleStart, ruleEnd);

    for (const selector of DISCLOSURE_TOGGLE_SELECTORS) {
      expect(rule, `${selector} not part of the shared touch-target rule`).toContain(selector);
    }
    expect(rule).toContain("min-height: var(--size-control-min)");
    // A hit target sized only by min-height is still text-width-only on the
    // inline axis -- the rule needs horizontal padding too.
    expect(rule).toMatch(/padding:\s*\S+\s+0\.\d+rem\s*;/);
  });
});
