import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import type { LineageGraph } from "./api";
import { LineageDag } from "./LineageDag";

const edgeTargetGraph: LineageGraph = {
  nodes: [
    {
      id: "rec-001",
      group: "A-100",
      label: "Initial site visit",
      occurred_at: "2026-01-01T00:00:00Z",
      is_root: true,
      is_branch_point: false,
    },
    {
      id: "rec-002",
      group: "A-100",
      label: "Pricing follow-up",
      occurred_at: "2026-01-02T00:00:00Z",
      is_root: false,
      is_branch_point: false,
    },
  ],
  edges: [
    {
      source: "rec-001",
      target: "rec-002",
      fused_score: 0.8,
    },
  ],
};

describe("LineageDag edge pointer target", () => {
  it("gives a connection at least a 24px pointer corridor without duplicating its accessible button", () => {
    const { container } = render(<LineageDag graph={edgeTargetGraph} onSelectPost={vi.fn()} />);

    expect(
      screen.getAllByRole("button", {
        name: "Open connection evidence: Initial site visit to Pricing follow-up",
      }),
    ).toHaveLength(1);

    const hitTarget = container.querySelector(".lineage-dag-edge-hit");
    expect(hitTarget).not.toBeNull();
    expect(hitTarget).toHaveAttribute("aria-hidden", "true");
    expect(hitTarget).toHaveAttribute("pointer-events", "stroke");
    expect(Number(hitTarget?.getAttribute("stroke-width"))).toBeGreaterThanOrEqual(24);
  });
});
