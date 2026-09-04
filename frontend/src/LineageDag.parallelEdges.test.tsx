import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import type { LineageGraph } from "./api";
import { LineageDag } from "./LineageDag";
import { setLocale } from "./i18n";

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

afterEach(() => setLocale("en"));

describe("LineageDag parallel edge identity", () => {
  it("keeps source/target-identical edge evidence controls independently identifiable and selectable", async () => {
    render(<LineageDag graph={parallelEdgeGraph} onSelectPost={vi.fn()} />);

    const edgeButtons = screen.getAllByRole("button", {
      name: /Open connection evidence: Initial site visit to Pricing follow-up/,
    });
    expect(edgeButtons).toHaveLength(2);
    expect(new Set(edgeButtons.map((button) => button.getAttribute("aria-label"))).size).toBe(2);
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

  it("preserves selected parallel-edge context when an unrelated earlier edge appears", async () => {
    const { rerender } = render(<LineageDag graph={parallelEdgeGraph} onSelectPost={vi.fn()} />);
    const edgeButtons = screen.getAllByRole("button", {
      name: /Open connection evidence: Initial site visit to Pricing follow-up/,
    });
    const selectedLabel = edgeButtons[0].getAttribute("aria-label");
    expect(selectedLabel).toBeTruthy();

    await userEvent.click(edgeButtons[0]);
    expect(edgeButtons[0]).toHaveAttribute("aria-pressed", "true");

    const graphWithEarlierEdge: LineageGraph = {
      nodes: [
        {
          id: "rec-000",
          group: "A-100",
          label: "Account created",
          occurred_at: "2025-12-31T00:00:00Z",
          is_root: true,
          is_branch_point: false,
        },
        ...parallelEdgeGraph.nodes,
      ],
      edges: [
        {
          source: "rec-000",
          target: "rec-001",
          fused_score: 0.9,
        },
        ...parallelEdgeGraph.edges,
      ],
    };

    rerender(<LineageDag graph={graphWithEarlierEdge} onSelectPost={vi.fn()} />);

    expect(screen.getByRole("button", { name: selectedLabel! })).toHaveAttribute("aria-pressed", "true");
    expect(screen.getAllByRole("button", {
      name: /Open connection evidence: Initial site visit to Pricing follow-up/,
    }).filter((button) => button.getAttribute("aria-pressed") === "true")).toHaveLength(1);
  });

  it("renders channel evidence by canonical rank regardless of transport array order", () => {
    const graphWithOutOfOrderEvidence: LineageGraph = {
      nodes: parallelEdgeGraph.nodes,
      edges: [
        {
          ...parallelEdgeGraph.edges[0],
          channel_evidence: [
            {
              signal_code: "temporal",
              signal_label: "Temporal proximity",
              score: 0.7,
              weight: 0.5,
              contribution: 0.35,
              rank: 2,
            },
            parallelEdgeGraph.edges[0].channel_evidence![0],
          ],
        },
      ],
    };

    render(<LineageDag graph={graphWithOutOfOrderEvidence} onSelectPost={vi.fn()} />);

    const disclosure = screen.getByText(/fused score 0\.810000/).closest("details");
    expect(disclosure).not.toBeNull();
    const rows = within(disclosure!).getAllByRole("row");
    expect(rows[1]).toHaveTextContent("Text similarity");
    expect(rows[2]).toHaveTextContent("Temporal proximity");
  });

  it("does not append untranslated English disambiguation to Korean parallel-edge controls", () => {
    setLocale("ko");
    render(<LineageDag graph={parallelEdgeGraph} onSelectPost={vi.fn()} />);

    const edgeButtons = screen.getAllByRole("button", { name: /연결 근거 열기/ });
    expect(edgeButtons).toHaveLength(2);
    for (const button of edgeButtons) {
      expect(button.getAttribute("aria-label")).not.toMatch(/relationship|fused score/i);
    }
  });
});
