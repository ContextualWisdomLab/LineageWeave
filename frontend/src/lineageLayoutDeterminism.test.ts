import { describe, expect, it } from "vitest";
import { layoutLineageDag } from "./lineageLayout";

function canonicalPositions(graph: Parameters<typeof layoutLineageDag>[0]) {
  return layoutLineageDag(graph)
    .flatMap((group) => group.nodes)
    .map(({ id, x, y }) => ({ id, x, y }))
    .sort((left, right) => (left.id < right.id ? -1 : left.id > right.id ? 1 : 0));
}

describe("layoutLineageDag deterministic geometry", () => {
  it("keeps node geometry stable when equivalent graph arrays arrive in a different order", () => {
    const nodes = ["root", "branch-a", "branch-b"].map((id) => ({
      id,
      group: "Project Alpha",
      label: id,
      occurred_at: "2026-09-01T00:00:00Z",
      is_root: id === "root",
      is_branch_point: id === "root",
    }));
    const edges = [
      { source: "root", target: "branch-a", fused_score: 0.91 },
      { source: "root", target: "branch-b", fused_score: 0.89 },
    ];

    const forward = canonicalPositions({ nodes, edges });
    const reordered = canonicalPositions({
      nodes: [...nodes].reverse(),
      edges: [...edges].reverse(),
    });

    expect(reordered).toEqual(forward);
  });
});
