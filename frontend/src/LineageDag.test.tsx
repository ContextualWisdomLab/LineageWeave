import { render, screen, within } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { LineageDag } from "./LineageDag";
import type { LineageGraph } from "./api";
import { setLocale } from "./i18n";

const graph: LineageGraph = {
  nodes: [
    {
      id: "post-a",
      group: "Apollo",
      label: "Initial event",
      occurred_at: "2026-01-01T00:00:00Z",
      is_root: true,
      is_branch_point: false,
    },
    {
      id: "post-b",
      group: "Apollo",
      label: "Follow-up event",
      occurred_at: "2026-01-02T00:00:00Z",
      is_root: false,
      is_branch_point: false,
    },
  ],
  edges: [
    {
      source: "post-a",
      target: "post-b",
      fused_score: 0.78,
      channel_scores: {
        temporal: 0.9,
        secondary_key: 1,
        text: 0.42,
      },
    },
  ],
};

describe("LineageDag evidence disclosure", () => {
  beforeEach(() => {
    setLocale("en");
  });

  it("renders an exact-value table and does not invent an unavailable LLM score", () => {
    render(<LineageDag graph={graph} onSelectPost={vi.fn()} />);

    const table = screen.getByRole("table", { name: "Lineage evidence scores" });
    const row = within(table).getByRole("row", {
      name: /Initial event Follow-up event 0\.7800 0\.9000 1\.0000 0\.4200 Not available/,
    });

    expect(row).toBeInTheDocument();
    expect(
      screen.getByText("Review exact channel scores before relying on this connection."),
    ).toBeInTheDocument();
    expect(screen.queryByText("0.0000")).not.toBeInTheDocument();
  });

  it("includes the same evidence in the SVG edge description", () => {
    const { container } = render(
      <LineageDag graph={graph} onSelectPost={vi.fn()} />,
    );

    const edgeTitle = container.querySelector(".lineage-dag-edge title");
    expect(edgeTitle?.textContent).toContain("Fused score 0.7800");
    expect(edgeTitle?.textContent).toContain("Time proximity 0.9000");
    expect(edgeTitle?.textContent).toContain("Secondary-key match 1.0000");
    expect(edgeTitle?.textContent).toContain("Text similarity 0.4200");
    expect(edgeTitle?.textContent).not.toContain("LLM adjudication 0.0000");
  });
});
