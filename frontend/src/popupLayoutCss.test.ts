/// <reference types="node" />
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";

const here = dirname(fileURLToPath(import.meta.url));
const css = readFileSync(join(here, "App.css"), "utf-8");

describe("popup layout CSS contract", () => {
  it("uses the shared three-tier layout without a fourth popup breakpoint", () => {
    expect(css).toContain("width: min(90%, 1180px);");
    expect(css).not.toContain("@media (min-width: 1280px)");
    expect(css).toContain(".popup-secondary-grid");
    expect(css).toContain(".popup-secondary-grid > .popup-section:only-child");
  });
});
