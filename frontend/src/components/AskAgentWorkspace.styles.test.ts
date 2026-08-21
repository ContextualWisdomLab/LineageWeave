/// <reference types="node" />
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";

const here = dirname(fileURLToPath(import.meta.url));
const componentCss = readFileSync(join(here, "AskAgentWorkspace.css"), "utf-8");
const tokensCss = readFileSync(join(here, "..", "styles", "tokens.css"), "utf-8");
const [lightBlock, darkBlock] = tokensCss.split("@media (prefers-color-scheme: dark)");

const PRIMARY_ACTION_TOKENS = [
  "--color-btn-primary-bg",
  "--color-btn-primary-hover",
  "--color-btn-primary-text",
];

describe("Ask Agent design-token contract", () => {
  it("defines every primary-action token in both color modes", () => {
    for (const token of PRIMARY_ACTION_TOKENS) {
      expect(lightBlock).toContain(`${token}:`);
      expect(darkBlock).toContain(`${token}:`);
    }
  });

  it("uses primary-action tokens instead of inline color literals", () => {
    for (const token of PRIMARY_ACTION_TOKENS) {
      expect(componentCss).toContain(`var(${token})`);
    }
    expect(componentCss.toLowerCase()).not.toContain("color: #fff");
    expect(componentCss.toLowerCase()).not.toContain("background: #034ea2");
  });

  it("keeps the three responsive layout bands explicit", () => {
    expect(componentCss).toContain("@media (max-width: 1024px)");
    expect(componentCss).toContain("@media (max-width: 768px)");
  });
});
