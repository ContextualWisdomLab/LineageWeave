import { describe, expect, it } from "vitest";
import { layoutLineageDag } from "./lineageLayout";


describe("layoutLineageDag visible-cycle integrity", () => {
  it("fails closed when visible predecessor edges form a directed cycle", () => {
    const graph = {
      nodes: ["post-a", "post-b", "post-c"].map((id) => ({
        id,
        group: "Project Alpha",
        label: id,
        occurred_at: "2026-09-01T00:00:00Z",
        is_root: false,
        is_branch_point: true,
      })),
      edges: [
        { source: "post-a", target: "post-b", fused_score: 0.91 },
        { source: "post-b", target: "post-c", fused_score: 0.89 },
        { source: "post-c", target: "post-a", fused_score: 0.87 },
      ],
    };

    expect(() => layoutLineageDag(graph)).toThrow(/cyclic visible lineage edges/);
  });
});
