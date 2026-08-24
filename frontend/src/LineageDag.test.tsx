import { fireEvent, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { LineageDag } from "./LineageDag";
import type { LineageGraph } from "./api";

const a100Graph: LineageGraph = {
  nodes: [
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
  ],
  edges: [
    {
      source: "rec-002",
      target: "rec-003",
      fused_score: 0.9,
      interval_relation_code: "interval_contains",
      interval_relation_label: "Contains",
    },
    {
      source: "rec-002",
      target: "rec-004",
      fused_score: 0.85,
      interval_relation_code: "interval_overlaps",
      interval_relation_label: "Overlaps",
    },
  ],
};

describe("LineageDag", () => {
  it("shows Contains and Overlaps as visible text, not hover-only", () => {
    const { container } = render(
      <LineageDag graph={a100Graph} onSelectPost={() => undefined} currentPostId="rec-002" />,
    );
    expect(screen.getAllByText("Contains").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Overlaps").length).toBeGreaterThan(0);
    expect(screen.getByRole("list", { name: "Interval relations" })).toBeInTheDocument();
    expect(container.querySelector("path title")).toHaveTextContent(
      "Pricing renegotiation: revised quote sent follows Pricing renegotiation follow-up",
    );
  });

  it("opens the revised quote from the Contains keyboard row", async () => {
    const onSelectPost = vi.fn();
    render(<LineageDag graph={a100Graph} onSelectPost={onSelectPost} currentPostId="rec-002" />);
    await userEvent.click(
      screen.getByRole("button", {
        name: "Pricing renegotiation follow-up relates to Pricing renegotiation: revised quote sent as Contains; open Pricing renegotiation: revised quote sent",
      }),
    );
    expect(onSelectPost).toHaveBeenCalledWith("rec-003");
  });

  it("keeps the stored parent-to-child direction when the child is current", async () => {
    const onSelectPost = vi.fn();
    render(<LineageDag graph={a100Graph} onSelectPost={onSelectPost} currentPostId="rec-003" />);
    await userEvent.click(
      screen.getByRole("button", {
        name: "Pricing renegotiation follow-up relates to Pricing renegotiation: revised quote sent as Contains; open Pricing renegotiation follow-up",
      }),
    );
    expect(onSelectPost).toHaveBeenCalledWith("rec-002");
  });

  it("shows an empty-state message instead of an empty graph", () => {
    render(<LineageDag graph={{ nodes: [], edges: [] }} onSelectPost={vi.fn()} />);
    expect(screen.getByText("No reconstructed lineage yet. Rebuild after seeding posts.")).toBeInTheDocument();
    expect(screen.queryByRole("img")).not.toBeInTheDocument();
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
    expect(screen.getAllByRole("img")).toHaveLength(2);
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
    render(<LineageDag graph={graph} onSelectPost={vi.fn()} />);

    const headings = screen.getAllByRole("img").map((img) => img.getAttribute("aria-label"));
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
