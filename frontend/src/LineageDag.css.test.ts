/// <reference types="node" />
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";

const here = dirname(fileURLToPath(import.meta.url));
const css = readFileSync(join(here, "LineageDag.css"), "utf-8");
const appCss = readFileSync(join(here, "App.css"), "utf-8");

describe("LineageDag CSS contracts", () => {
  it("keeps the event-date selector at least as specific as the shared node-text rule", () => {
    expect(css).toContain(".lineage-dag-node text.lineage-dag-node-date {");
    expect(css).not.toMatch(/(^|\n)\.lineage-dag-node-date\s*\{/);
  });

  it("does not override each edge's instance-specific SVG marker", () => {
    expect(appCss).not.toContain('marker-end: url("#lineage-dag-arrow");');
  });

  it("uses each localized cell label in the mobile evidence layout", () => {
    expect(appCss).toContain("content: attr(data-label);");
    expect(appCss).not.toContain('content: "Graph relation";');
    expect(appCss).not.toContain('content: "Evidence (fused_score)";');
  });

  it("keeps the buyer board controls as one stacked layout contract", () => {
    for (const selector of [
      "board-header",
      "board-result-count",
      "board-controls",
      "board-voc-type-filter",
      "post-body-excerpt",
      "board-empty",
      "board-pagination",
    ]) {
      expect(appCss.match(new RegExp(`(^|\\n)\\.${selector}\\s*\\{`, "g"))).toHaveLength(1);
    }
    expect(appCss).toContain(".board-search-row {");
    expect(appCss).not.toContain("grid-template-columns: minmax(12rem, 2fr)");
  });
});
