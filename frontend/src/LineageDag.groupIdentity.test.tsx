import { render, screen, within } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import type { LineageGraph } from "./api";
import { LineageDag } from "./LineageDag";

const graph: LineageGraph = {
  nodes: [
    {
      id: "alpha",
      group: "Alpha",
      label: "Alpha record",
      occurred_at: "2026-01-01T00:00:00Z",
      is_root: true,
      is_branch_point: false,
    },
    {
      id: "named-ungrouped",
      group: "Ungrouped",
      label: "Named Ungrouped record",
      occurred_at: "2026-01-02T00:00:00Z",
      is_root: true,
      is_branch_point: false,
    },
    {
      id: "truly-ungrouped",
      group: "",
      label: "Truly ungrouped record",
      occurred_at: "2026-01-03T00:00:00Z",
      is_root: true,
      is_branch_point: false,
    },
  ],
  edges: [],
};

describe("LineageDag reconstruct-group identity", () => {
  it("renders a named Ungrouped thread separately from records with no group", () => {
    const { container, rerender } = render(
      <LineageDag graph={graph} onSelectPost={vi.fn()} />,
    );

    const figures = [...container.querySelectorAll<HTMLElement>(".lineage-dag-group")];
    expect(figures).toHaveLength(3);
    expect(figures[0]).toHaveTextContent("Alpha record");
    expect(figures[1]).toHaveTextContent("Named Ungrouped record");
    expect(figures[1]).not.toHaveTextContent("Truly ungrouped record");
    expect(figures[2]).toHaveTextContent("Truly ungrouped record");
    expect(figures[2]).not.toHaveTextContent("Named Ungrouped record");
    expect(screen.getAllByRole("region", { name: "Ungrouped lineage viewport" })).toHaveLength(2);

    rerender(<LineageDag graph={graph} onSelectPost={vi.fn()} />);
    const rerendered = [...container.querySelectorAll<HTMLElement>(".lineage-dag-group")];
    expect(
      rerendered.map((figure) => within(figure).getByRole("button").getAttribute("aria-label")),
    ).toEqual([
      "Open post: Alpha record",
      "Open post: Named Ungrouped record",
      "Open post: Truly ungrouped record",
    ]);
  });
});
