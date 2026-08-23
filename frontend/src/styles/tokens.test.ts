/// <reference types="node" />
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";

const here = dirname(fileURLToPath(import.meta.url));
const tokensCss = readFileSync(join(here, "tokens.css"), "utf-8");
const appCss = readFileSync(join(here, "..", "App.css"), "utf-8");

const [lightBlock, darkBlock] = tokensCss.split("@media (prefers-color-scheme: dark)");

const EXCEPTION_SURFACE_TOKENS = [
  "--color-exception-background",
  "--color-exception-border",
  "--color-exception-accent",
  "--color-exception-text",
  "--color-exception-heading",
];

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

describe("design tokens", () => {
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

  it("gives native interactive controls a shared visible focus token", () => {
    expect(appCss).toContain("button:focus-visible");
    expect(appCss).toContain("outline: 2px solid var(--color-focus-border);");
    expect(appCss).toContain("outline-offset: 2px;");
  });

  it("defines exception-surface tokens in both the light and dark blocks", () => {
    for (const token of EXCEPTION_SURFACE_TOKENS) {
      expect(lightBlock, `${token} missing from the light :root block`).toContain(`${token}:`);
      expect(darkBlock, `${token} missing from the dark prefers-color-scheme block`).toContain(
        `${token}:`,
      );
    }
  });

  it("styles the exception surface with token var() references, not a new danger hex", () => {
    for (const token of EXCEPTION_SURFACE_TOKENS) {
      expect(appCss, `App.css never references var(${token})`).toContain(`var(${token})`);
    }
    expect(appCss).not.toMatch(/color-danger|#b42318/i);
  });
});
