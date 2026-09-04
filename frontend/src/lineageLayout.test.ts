import { describe, expect, it } from "vitest";
import { groupHeading, layoutLineageDag, subgraphForPost } from "./lineageLayout";

const a100Graph = {
  nodes: [
    {
      id: "rec-001",
      group: "A-100",
      label: "Initial site visit and project scope discussion",
      occurred_at: "2026-01-01T00:00:00",
      is_root: true,
      is_branch_point: false,
    },
    {
      id: "rec-002",
      group: "A-100",
      label: "Pricing renegotiation follow-up",
      occurred_at: "2026-01-06T00:00:00",
      is_root: false,
      is_branch_point: true,
    },
    {
      id: "rec-003",
      group: "A-100",
      label: "Pricing renegotiation: revised quote sent",
      occurred_at: "2026-01-10T00:00:00",
      is_root: false,
      is_branch_point: false,
    },
    {
      id: "rec-004",
      group: "A-100",
      label: "Delivery schedule question raised",
      occurred_at: "2026-01-07T00:00:00",
      is_root: false,
      is_branch_point: false,
    },
    {
      id: "rec-005",
      group: "A-100",
      label: "Delivery schedule confirmed with logistics",
      occurred_at: "2026-01-12T00:00:00",
      is_root: false,
      is_branch_point: false,
    },
    {
      id: "rec-006",
      group: "A-100",
      label: "Unrelated: annual account review",
      occurred_at: "2026-02-10T00:00:00",
      is_root: true,
      is_branch_point: false,
    },
    {
      id: "rec-101",
      group: "B-200",
      label: "Technical specification review meeting",
      occurred_at: "2026-01-03T00:00:00",
      is_root: true,
      is_branch_point: false,
    },
  ],
  edges: [
    { source: "rec-001", target: "rec-002", fused_score: 0.8 },
    { source: "rec-002", target: "rec-003", fused_score: 0.9 },
    { source: "rec-002", target: "rec-004", fused_score: 0.85 },
    { source: "rec-004", target: "rec-005", fused_score: 0.8 },
  ],
};

describe("layoutLineageDag", () => {
  it("keeps A-100 and B-200 as separate groups and rec-006 as an A-100 root", () => {
    const groups = layoutLineageDag(a100Graph);
    expect(groups.map((group) => group.heading)).toEqual(["A-100", "B-200"]);
    const a100 = groups[0];
    const fork = a100.nodes.find((node) => node.id === "rec-002");
    const quote = a100.nodes.find((node) => node.id === "rec-003");
    const delivery = a100.nodes.find((node) => node.id === "rec-004");
    const isolated = a100.nodes.find((node) => node.id === "rec-006");
    expect(fork?.is_branch_point).toBe(true);
    expect(quote && delivery && fork).toBeTruthy();
    expect(quote!.x).toBe(delivery!.x);
    expect(quote!.x).toBeGreaterThan(fork!.x);
    expect(quote!.y).not.toBe(delivery!.y);
    expect(isolated?.is_root).toBe(true);
    expect(isolated!.x).toBeLessThan(fork!.x);
  });

  it("scopes a post's popup DAG to its reconstruct group, including the A-100 fork", () => {
    const scoped = subgraphForPost(a100Graph, "rec-002");
    expect(scoped.nodes.map((node) => node.id).sort()).toEqual([
      "rec-001",
      "rec-002",
      "rec-003",
      "rec-004",
      "rec-005",
      "rec-006",
    ]);
    expect(scoped.nodes.some((node) => node.group === "B-200")).toBe(false);
    expect(scoped.edges.filter((edge) => edge.source === "rec-002").map((edge) => edge.target).sort()).toEqual([
      "rec-003",
      "rec-004",
    ]);
  });

  it("returns an empty graph when the post is not in the reconstruct DAG", () => {
    expect(subgraphForPost(a100Graph, "missing-post")).toEqual({ nodes: [], edges: [] });
  });

  it("labels UUID reconstruct fallbacks as Ungrouped without merging named threads", () => {
    expect(groupHeading("A-100")).toBe("A-100");
    expect(groupHeading("")).toBe("Ungrouped");
    expect(groupHeading("cccccccc-cccc-cccc-cccc-cccccccccccc")).toBe("Ungrouped");
    expect(
      layoutLineageDag({
        nodes: [
          {
            id: "named",
            group: "Named thread",
            label: "Named note",
            occurred_at: "2026-01-01T00:00:00Z",
            is_root: true,
            is_branch_point: false,
          },
          {
            id: "loose",
            group: "",
            label: "Loose note",
            occurred_at: "2026-01-02T00:00:00Z",
            is_root: true,
            is_branch_point: false,
          },
        ],
        edges: [],
      }).map((group) => group.heading),
    ).toEqual(["Named thread", "Ungrouped"]);
  });

  it("rejects a cyclic visible component instead of inventing a root", () => {
    expect(() => layoutLineageDag({
      nodes: [
        {
          id: "cycle-a",
          group: "Cyclic import",
          label: "First imported note",
          occurred_at: "2026-01-01T00:00:00Z",
          is_root: false,
          is_branch_point: false,
        },
        {
          id: "cycle-b",
          group: "Cyclic import",
          label: "Second imported note",
          occurred_at: "2026-01-02T00:00:00Z",
          is_root: false,
          is_branch_point: false,
        },
      ],
      edges: [
        { source: "cycle-a", target: "cycle-b", fused_score: 0.8 },
        { source: "cycle-b", target: "cycle-a", fused_score: 0.79 },
      ],
    })).toThrow("cyclic visible lineage edges at: cycle-a");
  });

  it("rejects a visible root that feeds a cycle", () => {
    expect(() => layoutLineageDag({
      nodes: ["root", "cycle-a", "cycle-b"].map((id) => ({
        id,
        group: "Cyclic import",
        label: id,
        occurred_at: "2026-01-01T00:00:00Z",
        is_root: id === "root",
        is_branch_point: false,
      })),
      edges: [
        { source: "root", target: "cycle-a", fused_score: 0.9 },
        { source: "cycle-a", target: "cycle-b", fused_score: 0.8 },
        { source: "cycle-b", target: "cycle-a", fused_score: 0.7 },
      ],
    })).toThrow("cyclic visible lineage edges at: cycle-a");
  });

  it("positions a shared child once while retaining both visible parent edges", () => {
    const [group] = layoutLineageDag({
      nodes: ["root", "branch-a", "branch-b", "shared-child"].map((id) => ({
        id,
        group: "Converging import",
        label: id,
        occurred_at: "2026-01-01T00:00:00Z",
        is_root: id === "root",
        is_branch_point: id === "root",
      })),
      edges: [
        { source: "root", target: "branch-a", fused_score: 0.9 },
        { source: "root", target: "branch-b", fused_score: 0.88 },
        { source: "branch-a", target: "shared-child", fused_score: 0.82 },
        { source: "branch-b", target: "shared-child", fused_score: 0.8 },
        { source: "root", target: "shared-child", fused_score: 0.78 },
      ],
    });

    expect(group.edges).toHaveLength(5);
    expect(group.nodes.map(({ id, x, y }) => ({ id, x, y }))).toEqual([
      { id: "branch-a", x: 248, y: 28 },
      { id: "branch-b", x: 248, y: 80 },
      { id: "root", x: 28, y: 54 },
      { id: "shared-child", x: 468, y: 28 },
    ]);
  });

  it("keeps a valid relationship between two ungrouped visible nodes", () => {
    const [group] = layoutLineageDag({
      nodes: [
        {
          id: "ungrouped-a",
          group: "",
          label: "First loose note",
          occurred_at: "2026-01-01T00:00:00Z",
          is_root: true,
          is_branch_point: false,
        },
        {
          id: "ungrouped-b",
          group: "",
          label: "Second loose note",
          occurred_at: "2026-01-02T00:00:00Z",
          is_root: false,
          is_branch_point: false,
        },
      ],
      edges: [{ source: "ungrouped-a", target: "ungrouped-b", fused_score: 0.88 }],
    });

    expect(group.heading).toBe("Ungrouped");
    expect(group.edges).toHaveLength(1);
  });

  it("omits dangling and cross-group edges from visible layout evidence", () => {
    const groups = layoutLineageDag({
      nodes: [
        {
          id: "visible-a",
          group: "Project Alpha",
          label: "Visible Alpha note",
          occurred_at: "2026-01-01T00:00:00Z",
          is_root: true,
          is_branch_point: false,
        },
        {
          id: "visible-b",
          group: "Project Beta",
          label: "Visible Beta note",
          occurred_at: "2026-01-02T00:00:00Z",
          is_root: true,
          is_branch_point: false,
        },
      ],
      edges: [
        { source: "visible-a", target: "hidden-note", fused_score: 0.91 },
        { source: "visible-a", target: "visible-b", fused_score: 0.84 },
        { source: "hidden-note", target: "visible-a", fused_score: 0.77 },
      ],
    });

    expect(groups.map((group) => [group.heading, group.edges])).toEqual([
      ["Project Alpha", []],
      ["Project Beta", []],
    ]);
  });
});
