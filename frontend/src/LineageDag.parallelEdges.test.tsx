import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import type { LineageGraph } from "./api";
import { LineageDag } from "./LineageDag";

const parallelEdgeGraph: LineageGraph = {
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
      fused_score: 0.81,
      interval_relation_code: "interval_contains",
      interval_relation_label: "Contains",
      channel_evidence: [
        {
          signal_code: "text",
          signal_label: "Text similarity",
          score: 0.81,
          weight: 1,
          contribution: 0.81,
          rank: 1,
        },
      ],
    },
    {
      source: "rec-001",
      target: "rec-002",
      fused_score: 0.67,
      interval_relation_code: "interval_overlaps",
      interval_relation_label: "Overlaps",
      channel_evidence: [
        {
          signal_code: "temporal",
          signal_label: "Temporal proximity",
          score: 0.67,
          weight: 1,
          contribution: 0.67,
          rank: 1,
        },
      ],
    },
  ],
};

describe("LineageDag parallel edge identity", () => {
  it("keeps source/target-identical edge evidence controls independently selectable", async () => {
    render(<LineageDag graph={parallelEdgeGraph} onSelectPost={vi.fn()} />);

    const edgeButtons = screen.getAllByRole("button", {
      name: "Open connection evidence: Initial site visit to Pricing follow-up",
    });
    expect(edgeButtons).toHaveLength(2);
    expect(edgeButtons[0]).toHaveAttribute("aria-pressed", "false");
    expect(edgeButtons[1]).toHaveAttribute("aria-pressed", "false");

    await userEvent.click(edgeButtons[0]);

    expect(edgeButtons[0]).toHaveAttribute("aria-pressed", "true");
    expect(edgeButtons[1]).toHaveAttribute("aria-pressed", "false");

    const disclosures = screen
      .getAllByText(/fused score 0\.(670000|810000)/)
      .map((summary) => summary.closest("details"));
    expect(disclosures.filter((details) => details?.hasAttribute("open"))).toHaveLength(1);
  });
});
