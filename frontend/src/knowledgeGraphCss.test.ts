/// <reference types="node" />
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";

const here = dirname(fileURLToPath(import.meta.url));
const css = readFileSync(join(here, "KnowledgeGraph.css"), "utf-8");

describe("Knowledge Graph CSS contract", () => {
  it("never reintroduces the undefined --ink/--muted/--line/--line-strong/--warning custom properties", () => {
    // 2026-08-22 bug: these names were used throughout but never defined
    // anywhere in the app. An invalid var()/color-mix() falls back to
    // fill's own initial value (SVG: black), so "evidence" nodes rendered
    // as solid black boxes with black-on-black (invisible) text.
    for (const undefinedToken of ["--ink", "--muted", "--line-strong", "--line)", "--warning"]) {
      expect(css).not.toContain(`var(${undefinedToken}`);
    }
  });

  it("evidence nodes use a real, globally-defined color token", () => {
    expect(css).toContain("var(--color-accent-orange)");
  });
});
