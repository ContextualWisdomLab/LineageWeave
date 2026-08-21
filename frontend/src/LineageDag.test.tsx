import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import type { LineageGraph } from "./api";
import { LineageDag } from "./LineageDag";

const graph: LineageGraph = {
  nodes: [
    {
      id: "root-post",
      group: "synthetic-project",
      label: "Root record",
      occurred_at: "2026-01-01T00:00:00Z",
      is_root: true,
      is_branch_point: false,
    },
    {
      id: "child-post",
      group: "synthetic-project",
      label: "Child record",
      occurred_at: "2026-01-02T00:00:00Z",
      is_root: false,
      is_branch_point: false,
    },
  ],
  edges: [{ source: "root-post", target: "child-post", fused_score: 0.91 }],
};

describe("LineageDag", () => {
  it("renders the graph and opens a post from click and keyboard activation", async () => {
    const user = userEvent.setup();
    const onSelectPost = vi.fn();

    render(
      <LineageDag
        graph={graph}
        onSelectPost={onSelectPost}
        currentPostId="root-post"
      />,
    );

    expect(screen.getByRole("img", { name: "synthetic-project lineage" })).toBeInTheDocument();
    expect(document.querySelectorAll(".lineage-dag-edge")).toHaveLength(1);
    expect(screen.getByRole("button", { name: "Open post: Root record" })).toHaveAttribute(
      "aria-current",
      "true",
    );
    expect(screen.queryByRole("list")).not.toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Open post: Child record" }));
    expect(onSelectPost).toHaveBeenLastCalledWith("child-post");

    await user.keyboard("{Enter}");
    expect(onSelectPost).toHaveBeenLastCalledWith("child-post");
  });

  it("makes direction, scrolling, and exact edge evidence accessible without hover", () => {
    render(<LineageDag graph={graph} onSelectPost={vi.fn()} />);

    const arrowMarker = document.querySelector('marker[id^="lineage-dag-arrow-"]');
    expect(arrowMarker).not.toBeNull();

    const edge = document.querySelector(".lineage-dag-edge");
    expect(edge?.getAttribute("marker-end")).toMatch(/^url\(#lineage-dag-arrow-/);
    expect(edge).toHaveTextContent("Root record → Child record (0.91)");

    const scrollRegion = screen.getByRole("region", { name: /synthetic-project/ });
    expect(scrollRegion).toHaveClass("lineage-dag-scroll");
    expect(scrollRegion).toHaveAttribute("tabindex", "0");

    const evidenceTable = screen.getByRole("table", {
      name: "synthetic-project lineage — Evidence trail",
    });
    expect(within(evidenceTable).getByText("Root record → Child record")).toBeInTheDocument();
    expect(within(evidenceTable).getByText("0.91")).toBeInTheDocument();
    expect(within(evidenceTable).getByText("2026-01-01 → 2026-01-02")).toBeInTheDocument();
  });

  it("renders the explicit empty state without graph controls", () => {
    render(<LineageDag graph={{ nodes: [], edges: [] }} onSelectPost={vi.fn()} />);

    expect(screen.getByText("No reconstructed lineage yet. Rebuild after seeding posts.")).toBeInTheDocument();
    expect(screen.queryByRole("img")).not.toBeInTheDocument();
    expect(screen.queryByRole("table")).not.toBeInTheDocument();
  });
});
