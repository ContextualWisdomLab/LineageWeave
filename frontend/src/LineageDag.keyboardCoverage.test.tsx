import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import type { LineageGraph } from "./api";
import { LineageDag } from "./LineageDag";

const graph: LineageGraph = {
  nodes: [
    {
      id: "rec-001",
      group: "A-100",
      label: "Kickoff recap",
      occurred_at: "2026-01-02T00:00:00Z",
      is_root: true,
      is_branch_point: false,
    },
    {
      id: "rec-002",
      group: "A-100",
      label: "Pricing follow-up",
      occurred_at: "2026-01-03T00:00:00Z",
      is_root: false,
      is_branch_point: false,
    },
  ],
  edges: [
    {
      source: "rec-001",
      target: "rec-002",
      fused_score: 0.72,
      channel_evidence: [
        {
          signal_code: "llm",
          signal_label: "LLM adjudication",
          score: 0.8,
          weight: 0.4,
          contribution: 0.32,
          rank: 1,
        },
      ],
    },
  ],
  reconstruction: {
    reconstruction_version: "lineageweave.reconstruct/keyboard-coverage",
    generated_at: "2026-09-08T13:00:00Z",
    min_fused_score: 0.3,
    candidate_window: 50,
    active_weights: [
      { signal_code: "llm", signal_weight: 0.4 },
      { signal_code: "buyer_signal", signal_weight: 0.1 },
    ],
  },
};

function renderDag() {
  render(<LineageDag graph={graph} onSelectPost={vi.fn()} />);
  const edgeButton = screen.getByRole("button", {
    name: "Open connection evidence: Kickoff recap to Pricing follow-up",
  });
  const disclosure = screen.getByText(/fused score 0\.720000/).closest("details");
  if (!disclosure) throw new Error("expected connection evidence disclosure");
  return { edgeButton, disclosure };
}

describe("LineageDag connection keyboard coverage", () => {
  it("opens the same connection evidence with Enter as pointer activation", () => {
    const { edgeButton, disclosure } = renderDag();

    expect(disclosure).not.toHaveAttribute("open");
    fireEvent.keyDown(edgeButton, { key: "Enter" });

    expect(disclosure).toHaveAttribute("open");
    expect(edgeButton).toHaveAttribute("aria-pressed", "true");
    expect(screen.getByText("0.320000")).toBeInTheDocument();
  });

  it("opens the same connection evidence with Space", () => {
    const { edgeButton, disclosure } = renderDag();

    fireEvent.keyDown(edgeButton, { key: " " });

    expect(disclosure).toHaveAttribute("open");
    expect(edgeButton).toHaveAttribute("aria-pressed", "true");
  });

  it("does not activate connection evidence for unrelated keys", () => {
    const { edgeButton, disclosure } = renderDag();

    fireEvent.keyDown(edgeButton, { key: "Escape" });

    expect(disclosure).not.toHaveAttribute("open");
    expect(edgeButton).toHaveAttribute("aria-pressed", "false");
  });

  it("names LLM and unknown active-weight provenance without hiding either code path", () => {
    render(<LineageDag graph={graph} onSelectPost={vi.fn()} />);

    expect(screen.getByText(/LLM adjudication: 0\.400000/)).toBeInTheDocument();
    expect(screen.getByText(/buyer_signal: 0\.100000/)).toBeInTheDocument();
  });
});
