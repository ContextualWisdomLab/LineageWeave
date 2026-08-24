/// <reference types="node" />
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";

const here = dirname(fileURLToPath(import.meta.url));
const tokensCss = readFileSync(join(here, "tokens.css"), "utf-8");
const appCss = readFileSync(join(here, "..", "App.css"), "utf-8");

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
  const rgb = [1, 3, 5].map((i) => parseInt(hex.slice(i, i + 2), 16) / 255);
  const [r, g, b] = rgb.map((c) => (c <= 0.03928 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4));
  return 0.2126 * r + 0.7152 * g + 0.0722 * b;
}

function contrastRatio(hexA: string, hexB: string): number {
  const lA = relativeLuminance(hexA);
  const lB = relativeLuminance(hexB);
  const [lighter, darker] = lA > lB ? [lA, lB] : [lB, lA];
  return (lighter + 0.05) / (darker + 0.05);
}

function readToken(block: string, token: string): string {
  const match = block.match(new RegExp(`${token}:\\s*(#[0-9a-fA-F]{6})`));
  if (!match) throw new Error(`${token} not found as a hex value`);
  return match[1];
}

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
});
