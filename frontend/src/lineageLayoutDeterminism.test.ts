import { afterEach, describe, expect, it, vi } from "vitest";
import { layoutLineageDag, subgraphForPost } from "./lineageLayout";

afterEach(() => {
  vi.restoreAllMocks();
});

function canonicalPositions(graph: Parameters<typeof layoutLineageDag>[0]) {
  return layoutLineageDag(graph)
    .flatMap((group) => group.nodes)
    .map(({ id, x, y }) => ({ id, x, y }))
    .sort((left, right) => (left.id < right.id ? -1 : left.id > right.id ? 1 : 0));
}

function edgeOrder(graph: Parameters<typeof layoutLineageDag>[0]) {
  return layoutLineageDag(graph)
    .flatMap((group) => group.edges)
    .map(({ source, target, fused_score, interval_relation_code }) => ({
      source,
      target,
      fused_score,
      interval_relation_code,
    }));
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

  it("fails closed when two visible nodes claim one canonical node id", () => {
    const duplicateIdGraph = {
      nodes: [
        {
          id: "same-node",
          group: "Project Alpha",
          label: "First visible record",
          occurred_at: "2026-09-01T00:00:00Z",
          is_root: true,
          is_branch_point: false,
        },
        {
          id: "same-node",
          group: "Project Beta",
          label: "Conflicting visible record",
          occurred_at: "2026-09-02T00:00:00Z",
          is_root: true,
          is_branch_point: false,
        },
      ],
      edges: [],
    };

    expect(() => layoutLineageDag(duplicateIdGraph)).toThrow(/duplicate lineage node id: same-node/);
  });

  it("rejects duplicate canonical node identity before focus-group isolation can hide it", () => {
    const duplicateIdGraph = {
      nodes: [
        {
          id: "same-node",
          group: "Project Alpha",
          label: "First visible record",
          occurred_at: "2026-09-01T00:00:00Z",
          is_root: true,
          is_branch_point: false,
        },
        {
          id: "same-node",
          group: "Project Beta",
          label: "Conflicting visible record",
          occurred_at: "2026-09-02T00:00:00Z",
          is_root: true,
          is_branch_point: false,
        },
      ],
      edges: [],
    };

    expect(() => subgraphForPost(duplicateIdGraph, "same-node")).toThrow(
      /duplicate lineage node id: same-node/,
    );
  });

  it("orders timezone-offset timestamps by the represented event instant", () => {
    const nodes = [
      {
        id: "earlier-by-instant",
        group: "Project Alpha",
        label: "Earlier",
        occurred_at: "2026-09-01T01:00:00+02:00",
        is_root: true,
        is_branch_point: false,
      },
      {
        id: "later-by-instant",
        group: "Project Alpha",
        label: "Later",
        occurred_at: "2026-09-01T00:30:00Z",
        is_root: true,
        is_branch_point: false,
      },
    ];

    const forward = canonicalPositions({ nodes, edges: [] });
    const reordered = canonicalPositions({ nodes: [...nodes].reverse(), edges: [] });
    const earlier = forward.find((node) => node.id === "earlier-by-instant")!;
    const later = forward.find((node) => node.id === "later-by-instant")!;

    expect(earlier.y).toBeLessThan(later.y);
    expect(reordered).toEqual(forward);
  });

  it("does not assign browser-local timezone semantics to offsetless source timestamps", () => {
    const parse = Date.parse.bind(Date);
    vi.spyOn(Date, "parse").mockImplementation((value) => {
      if (!/(?:[zZ]|[+-]\d{2}:\d{2})$/.test(value)) {
        throw new Error("offsetless source time must not be parsed as browser-local time");
      }
      return parse(value);
    });

    const nodes = [
      {
        id: "early-naive",
        group: "Project Alpha",
        label: "Early naive",
        occurred_at: "2026-09-01T00:00:00",
        is_root: true,
        is_branch_point: false,
      },
      {
        id: "late-naive",
        group: "Project Alpha",
        label: "Late naive",
        occurred_at: "2026-09-01T01:00:00",
        is_root: true,
        is_branch_point: false,
      },
    ];

    const positions = canonicalPositions({ nodes, edges: [] });
    const early = positions.find((node) => node.id === "early-naive")!;
    const late = positions.find((node) => node.id === "late-naive")!;

    expect(early.y).toBeLessThan(late.y);
  });

  it("keeps parallel edge order stable when equivalent edges arrive in a different order", () => {
    const nodes = ["root", "child"].map((id) => ({
      id,
      group: "Project Alpha",
      label: id,
      occurred_at: "2026-09-01T00:00:00Z",
      is_root: id === "root",
      is_branch_point: id === "root",
    }));
    const edges = [
      {
        source: "root",
        target: "child",
        fused_score: 0.91,
        interval_relation_code: "before",
      },
      {
        source: "root",
        target: "child",
        fused_score: 0.73,
        interval_relation_code: "overlaps",
      },
    ];

    const forward = edgeOrder({ nodes, edges });
    const reordered = edgeOrder({ nodes, edges: [...edges].reverse() });

    expect(reordered).toEqual(forward);
  });
});
