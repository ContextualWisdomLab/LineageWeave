import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { LineageDag } from "./LineageDag";
import type { LineageGraph } from "./api";

const wideGraph: LineageGraph = {
  nodes: [
    { id: "a1", group: "A-100", label: "Initial scope", occurred_at: "2026-01-01T00:00:00Z", is_root: true, is_branch_point: false },
    { id: "a2", group: "A-100", label: "Terms follow-up", occurred_at: "2026-01-05T00:00:00Z", is_root: false, is_branch_point: false },
    { id: "a3", group: "A-100", label: "Delivery question", occurred_at: "2026-01-06T00:00:00Z", is_root: false, is_branch_point: false },
    { id: "a4", group: "A-100", label: "Delivery confirmed", occurred_at: "2026-01-11T00:00:00Z", is_root: false, is_branch_point: false },
  ],
  edges: [
    { source: "a1", target: "a2", fused_score: 0.83 },
    { source: "a2", target: "a3", fused_score: 0.87 },
    { source: "a3", target: "a4", fused_score: 0.9 },
  ],
};

describe("LineageDag responsive viewport", () => {
  it("keeps an intrinsically wide DAG inside a named keyboard-focusable viewport", () => {
    render(<LineageDag graph={wideGraph} onSelectPost={vi.fn()} />);

    expect(screen.getByText("Swipe or use arrow keys to inspect the full lineage.")).toBeInTheDocument();

    const viewport = screen.getByRole("region", { name: "A-100 lineage viewport" });
    expect(viewport).toHaveAttribute("tabindex", "0");
    expect(viewport).toHaveClass("lineage-dag-viewport");

    const svg = screen.getByRole("group", { name: "A-100 lineage" });
    expect(viewport).toContainElement(svg);
    expect(Number(svg.getAttribute("width"))).toBeGreaterThan(320);
  });
});
