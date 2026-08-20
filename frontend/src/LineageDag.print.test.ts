import { describe, expect, it } from "vitest";
import css from "./LineageDag.css?raw";

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
