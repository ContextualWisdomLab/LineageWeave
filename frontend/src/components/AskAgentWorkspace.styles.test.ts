/// <reference types="node" />
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";

const here = dirname(fileURLToPath(import.meta.url));
const componentCss = readFileSync(join(here, "AskAgentWorkspace.css"), "utf-8");
const tokensCss = readFileSync(join(here, "..", "styles", "tokens.css"), "utf-8");
const [lightBlock, darkBlock] = tokensCss.split("@media (prefers-color-scheme: dark)");

describe("Ask Agent design-token contract", () => {
  it("defines the primary-action foreground in both color modes", () => {
    expect(lightBlock).toContain("--color-on-accent:");
    expect(darkBlock).toContain("--color-on-accent:");
  });

  it("uses the primary-action foreground token instead of an inline literal", () => {
    expect(componentCss).toContain("color: var(--color-on-accent);");
    expect(componentCss.toLowerCase()).not.toContain("color: #fff");
  });

  it("keeps the three responsive layout bands explicit", () => {
    expect(componentCss).toContain("@media (max-width: 1024px)");
    expect(componentCss).toContain("@media (max-width: 768px)");
  });
});
