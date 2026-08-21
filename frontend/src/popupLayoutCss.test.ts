/// <reference types="node" />
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";

const here = dirname(fileURLToPath(import.meta.url));
const css = readFileSync(join(here, "App.css"), "utf-8");

describe("popup layout CSS contract", () => {
  it("widens the popup for desktop evidence grids and keeps the secondary grid responsive", () => {
    expect(css).toContain("width: min(85%, 1180px);");
    expect(css).toContain(".popup-secondary-grid");
    expect(css).toContain(".popup-secondary-grid > .popup-section:only-child");
  });
});
