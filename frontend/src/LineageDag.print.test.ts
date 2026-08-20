import { readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";

const css = readFileSync("src/LineageDag.css", "utf8");

describe("LineageDag print contract", () => {
  it("overrides the global print hiding rule and preserves exact evidence", () => {
    expect(css).toContain("@media print");
    expect(css).toContain(".lineage-dag,");
    expect(css).toContain(".lineage-dag *");
    expect(css).toContain("visibility: visible");
    expect(css).toContain(".lineage-evidence-table");
    expect(css).toContain("overflow: visible");
  });
});
