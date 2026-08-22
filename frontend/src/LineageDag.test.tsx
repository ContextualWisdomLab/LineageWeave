import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { LineageDag } from "./LineageDag";
import type { LineageGraph } from "./api";

describe("LineageDag", () => {
  it("shows an empty-state message instead of an empty graph", () => {
    render(<LineageDag graph={{ nodes: [], edges: [] }} onSelectPost={vi.fn()} />);
    expect(screen.getByText("No reconstructed lineage yet. Rebuild after seeding posts.")).toBeInTheDocument();
    expect(screen.queryByRole("img")).not.toBeInTheDocument();
  });

  it("renders one branch figure per lineage group, git-branch style", () => {
    const graph: LineageGraph = {
      nodes: [
        { id: "a1", group: "Project Alpha", label: "Kickoff note", occurred_at: "2026-01-01T00:00:00Z", is_root: true, is_branch_point: false },
        { id: "a2", group: "Project Alpha", label: "Follow-up note", occurred_at: "2026-01-02T00:00:00Z", is_root: false, is_branch_point: false },
        { id: "b1", group: "Project Beta", label: "Beta kickoff", occurred_at: "2026-01-03T00:00:00Z", is_root: true, is_branch_point: false },
      ],
      edges: [{ source: "a1", target: "a2", fused_score: 0.82 }],
    };
    render(<LineageDag graph={graph} onSelectPost={vi.fn()} />);

    expect(screen.getByText("Project Alpha (2 records, 1 lineage edges)")).toBeInTheDocument();
    expect(screen.getByText("Project Beta (1 records, 0 lineage edges)")).toBeInTheDocument();
    expect(screen.getAllByRole("img")).toHaveLength(2);
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
});
