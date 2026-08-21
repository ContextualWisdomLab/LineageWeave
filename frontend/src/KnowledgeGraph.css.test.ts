/// <reference types="node" />
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";

const here = dirname(fileURLToPath(import.meta.url));
const css = readFileSync(join(here, "KnowledgeGraph.css"), "utf-8");

describe("Knowledge Graph CSS contract", () => {
  it("uses only defined shared tokens for graph colors", () => {
    expect(css).not.toMatch(/var\(\s*--(?:ink|muted|line|line-strong|warning)\b/);
    expect(css).toContain("var(--color-accent-orange)");
  });
});
