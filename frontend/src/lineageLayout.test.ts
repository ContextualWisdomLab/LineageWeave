import { describe, expect, it } from "vitest";
import { groupHeading, layoutLineageDag } from "./lineageLayout";

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

  it("labels UUID reconstruct fallbacks as Ungrouped without merging named threads", () => {
    expect(groupHeading("A-100")).toBe("A-100");
    expect(groupHeading("cccccccc-cccc-cccc-cccc-cccccccccccc")).toBe("Ungrouped");
  });
});
