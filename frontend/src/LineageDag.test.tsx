import { fireEvent, render, screen } from "@testing-library/react";
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
    const disclosure = screen.getByText(/fused score 0.700000/).closest("details");
    const edgeButton = screen.getByRole("button", {
      name: "Open connection evidence: Kickoff recap to Pricing follow-up",
    });
    expect(screen.getByRole("group", { name: "A-100 lineage" })).toBeInTheDocument();
    expect(disclosure).not.toHaveAttribute("open");
    await userEvent.click(edgeButton);
    expect(disclosure).toHaveAttribute("open");
    expect(
      screen.getByText("Each connection is inferred from independent signals. It is not a causal claim."),
    ).toBeInTheDocument();
    expect(screen.getByText("No LLM adjudication participated in this connection.")).toBeInTheDocument();
    expect(screen.getByText("lineageweave.reconstruct/2.14.0")).toBeInTheDocument();
    expect(screen.getAllByText("0.250000").length).toBeGreaterThan(0);
    expect(screen.getByText("0.200000")).toBeInTheDocument();
    expect(screen.getByText(/fused score 0.700000/)).toBeInTheDocument();
    expect(screen.queryByText(/causal relationship/i)).not.toBeInTheDocument();
    expect(edgeButton).toHaveAttribute("tabindex", "0");
    expect(edgeButton).toHaveAttribute("aria-pressed", "true");
    await userEvent.click(screen.getByText(/fused score 0.700000/));
    expect(disclosure).not.toHaveAttribute("open");
    expect(edgeButton).toHaveAttribute("aria-pressed", "false");
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

describe("LineageDag", () => {
  it("shows an empty-state message instead of an empty graph", () => {
    render(<LineageDag graph={{ nodes: [], edges: [] }} onSelectPost={vi.fn()} />);
    expect(screen.getByText("No reconstructed lineage yet. Rebuild after seeding posts.")).toBeInTheDocument();
    expect(document.querySelector("svg")).not.toBeInTheDocument();
  });

  it("renders one branch figure per lineage group, git-branch style", () => {
    const graph: LineageGraph = {
      nodes: [
        { id: "a1", group: "Project Alpha", label: "Kickoff note", occurred_at: "2026-01-01T00:00:00Z", is_root: true, is_branch_point: true },
        { id: "a2", group: "Project Alpha", label: "Follow-up note", occurred_at: "2026-01-02T00:00:00Z", is_root: false, is_branch_point: false },
        { id: "b1", group: "Project Beta", label: "Beta kickoff", occurred_at: "2026-01-03T00:00:00Z", is_root: true, is_branch_point: false },
      ],
      edges: [{ source: "a1", target: "a2", fused_score: 0.82 }],
    };
    const { container } = render(<LineageDag graph={graph} onSelectPost={vi.fn()} />);

    expect(screen.getByText("Project Alpha (2 records, 1 lineage edges)")).toBeInTheDocument();
    expect(screen.getByText("Project Beta (1 records, 0 lineage edges)")).toBeInTheDocument();
    expect(container.querySelectorAll('svg[role="group"]')).toHaveLength(2);
    expect(container.querySelectorAll(".lineage-dag-edge")).toHaveLength(1);
    expect(container.querySelector(".lineage-dag-branch")).toBeInTheDocument();
    expect(container.querySelector(".lineage-dag-root")).toBeInTheDocument();
    expect(container.querySelector(".lineage-dag-node:not(.lineage-dag-root):not(.lineage-dag-branch)")).toBeInTheDocument();
  });

  it("groups a missing/UUID group id under an Ungrouped heading, sorted last", () => {
    const graph: LineageGraph = {
      nodes: [
        { id: "u1", group: "3f9c8b1a-1111-2222-3333-444455556666", label: "Loose note", occurred_at: "2026-01-01T00:00:00Z", is_root: true, is_branch_point: false },
        { id: "z1", group: "Zeta Corp", label: "Zeta note", occurred_at: "2026-01-01T00:00:00Z", is_root: true, is_branch_point: false },
      ],
      edges: [],
    };
    const { container } = render(<LineageDag graph={graph} onSelectPost={vi.fn()} />);

    const headings = [...container.querySelectorAll('svg[role="group"]')].map((svg) =>
      svg.getAttribute("aria-label"),
    );
    expect(headings).toEqual(["Zeta Corp lineage", "Ungrouped lineage"]);
  });

  it("reports the clicked post id", () => {
    const onSelectPost = vi.fn();
    const graph: LineageGraph = {
      nodes: [{ id: "a1", group: "Project Alpha", label: "Kickoff note", occurred_at: "2026-01-01T00:00:00Z", is_root: true, is_branch_point: false }],
      edges: [],
    };
    render(<LineageDag graph={graph} onSelectPost={onSelectPost} />);

    fireEvent.click(screen.getByRole("button", { name: "Open post: Kickoff note" }));
    expect(onSelectPost).toHaveBeenCalledWith("a1");
  });

  it("also selects a node via Enter and Space for keyboard users", () => {
    const onSelectPost = vi.fn();
    const graph: LineageGraph = {
      nodes: [{ id: "a1", group: "Project Alpha", label: "Kickoff note", occurred_at: "2026-01-01T00:00:00Z", is_root: true, is_branch_point: false }],
      edges: [],
    };
    render(<LineageDag graph={graph} onSelectPost={onSelectPost} />);

    const node = screen.getByRole("button", { name: "Open post: Kickoff note" });
    fireEvent.keyDown(node, { key: "Enter" });
    fireEvent.keyDown(node, { key: " " });
    expect(onSelectPost).toHaveBeenCalledTimes(2);
  });

  it("does not select on an unrelated key press", () => {
    const onSelectPost = vi.fn();
    const graph: LineageGraph = {
      nodes: [{ id: "a1", group: "Project Alpha", label: "Kickoff note", occurred_at: "2026-01-01T00:00:00Z", is_root: true, is_branch_point: false }],
      edges: [],
    };
    render(<LineageDag graph={graph} onSelectPost={onSelectPost} />);

    fireEvent.keyDown(screen.getByRole("button", { name: "Open post: Kickoff note" }), { key: "Tab" });
    expect(onSelectPost).not.toHaveBeenCalled();
  });

  it("marks the current post distinctly from the rest", () => {
    const graph: LineageGraph = {
      nodes: [
        { id: "a1", group: "Project Alpha", label: "Kickoff note", occurred_at: "2026-01-01T00:00:00Z", is_root: true, is_branch_point: false },
        { id: "a2", group: "Project Alpha", label: "Follow-up note", occurred_at: "2026-01-02T00:00:00Z", is_root: false, is_branch_point: false },
      ],
      edges: [{ source: "a1", target: "a2", fused_score: 0.5 }],
    };
    render(<LineageDag graph={graph} onSelectPost={vi.fn()} currentPostId="a2" />);

    expect(screen.getByRole("button", { name: "Open post: Follow-up note" })).toHaveAttribute("aria-current", "true");
    expect(screen.getByRole("button", { name: "Open post: Kickoff note" })).not.toHaveAttribute("aria-current");
  });

  it("truncates a very long node label instead of overflowing the graph", () => {
    const longLabel = "A".repeat(60);
    const graph: LineageGraph = {
      nodes: [{ id: "a1", group: "Project Alpha", label: longLabel, occurred_at: "2026-01-01T00:00:00Z", is_root: true, is_branch_point: false }],
      edges: [],
    };
    render(<LineageDag graph={graph} onSelectPost={vi.fn()} />);

    expect(screen.getByText(`${"A".repeat(33)}…`)).toBeInTheDocument();
    expect(screen.queryByText(longLabel)).not.toBeInTheDocument();
    // The full label is still reachable via the accessible name for screen readers.
    expect(screen.getByRole("button", { name: `Open post: ${longLabel}` })).toBeInTheDocument();
  });

  it("does not count or render a relationship whose other endpoint is not visible", () => {
    const graph: LineageGraph = {
      nodes: [
        {
          id: "visible-note",
          group: "Project Alpha",
          label: "Visible note",
          occurred_at: "2026-01-01T00:00:00Z",
          is_root: true,
          is_branch_point: false,
        },
      ],
      edges: [{ source: "visible-note", target: "hidden-note", fused_score: 0.92 }],
    };
    const { container } = render(<LineageDag graph={graph} onSelectPost={vi.fn()} />);

    expect(screen.getByText("Project Alpha (1 records, 0 lineage edges)")).toBeInTheDocument();
    expect(container.querySelector(".lineage-dag-edge")).not.toBeInTheDocument();
  });
});
