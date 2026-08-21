import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import type { LineageGraph } from "./api";
import { LineageDag } from "./LineageDag";

const graph: LineageGraph = {
  nodes: [
    {
      id: "rec-002",
      group: "A-100",
      label: "Kickoff recap",
      occurred_at: "2026-01-02T00:00:00",
      is_root: true,
      is_branch_point: true,
    },
    {
      id: "rec-003",
      group: "A-100",
      label: "Pricing follow-up",
      occurred_at: "2026-01-03T00:00:00",
      is_root: false,
      is_branch_point: false,
    },
  ],
  edges: [
    {
      source: "rec-002",
      target: "rec-003",
      fused_score: 0.7,
      channel_evidence: [
        {
          signal_code: "text",
          signal_label: "Text similarity",
          score: 0.5,
          weight: 0.5,
          contribution: 0.25,
          rank: 1,
        },
        {
          signal_code: "secondary_key",
          signal_label: "Secondary key match",
          score: 1.0,
          weight: 0.25,
          contribution: 0.25,
          rank: 2,
        },
        {
          signal_code: "temporal",
          signal_label: "Temporal proximity",
          score: 0.8,
          weight: 0.25,
          contribution: 0.2,
          rank: 3,
        },
      ],
    },
  ],
  reconstruction: {
    reconstruction_version: "lineageweave.reconstruct/2.14.0",
    generated_at: "2026-08-21T12:00:00+00:00",
    min_fused_score: 0.3,
    candidate_window: 50,
    active_weights: [
      { signal_code: "temporal", signal_weight: 0.25 },
      { signal_code: "secondary_key", signal_weight: 0.25 },
      { signal_code: "text", signal_weight: 0.5 },
    ],
  },
};

describe("LineageDag channel evidence", () => {
  it("discloses exact inferred values without hover-only interaction", async () => {
    render(<LineageDag graph={graph} onSelectPost={vi.fn()} />);
    expect(
      screen.getByText("Each connection is inferred from independent signals. It is not a causal claim."),
    ).toBeInTheDocument();
    expect(screen.getByText("No LLM adjudication participated in this connection.")).toBeInTheDocument();
    expect(screen.getByText("lineageweave.reconstruct/2.14.0")).toBeInTheDocument();
    expect(screen.getAllByText("0.250000").length).toBeGreaterThan(0);
    expect(screen.getByText("0.200000")).toBeInTheDocument();
    expect(screen.getByText(/fused score 0.700000/)).toBeInTheDocument();
    expect(screen.queryByText(/causal relationship/i)).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Open connection evidence: Kickoff recap to Pricing follow-up" })).toHaveAttribute(
      "tabindex",
      "0",
    );
  });

  it("does not claim a missing LLM channel when no evidence was recorded", () => {
    render(
      <LineageDag
        graph={{
          ...graph,
          edges: [{ source: "rec-002", target: "rec-003", fused_score: 0.7, channel_evidence: [] }],
          reconstruction: null,
        }}
        onSelectPost={vi.fn()}
      />,
    );
    expect(screen.queryByText("No LLM adjudication participated in this connection.")).not.toBeInTheDocument();
  });

  it("keeps the LLM channel visible when it participated", async () => {
    render(
      <LineageDag
        graph={{
          ...graph,
          edges: [
            {
              source: "rec-002",
              target: "rec-003",
              fused_score: 0.78,
              channel_evidence: [
                {
                  signal_code: "llm",
                  signal_label: "LLM adjudication",
                  score: 0.9,
                  weight: 0.4,
                  contribution: 0.36,
                  rank: 1,
                },
              ],
            },
          ],
        }}
        onSelectPost={vi.fn()}
      />,
    );
    await userEvent.click(screen.getByText(/fused score 0.780000/));
    expect(screen.getByText("LLM adjudication")).toBeInTheDocument();
    expect(screen.queryByText("No LLM adjudication participated in this connection.")).not.toBeInTheDocument();
  });
});
