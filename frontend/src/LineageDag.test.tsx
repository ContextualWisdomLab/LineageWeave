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
  edges: [
    {
      source: "root-post",
      target: "child-post",
      fused_score: 0.91,
      channel_scores: { temporal: 0.95, text: 0.6, llm: 0.8 },
    },
  ],
};

const isolatedGraph: LineageGraph = {
  nodes: [
    {
      id: "isolated-post",
      group: "isolated-project",
      label: "Unlinked record",
      occurred_at: "2026-02-01T00:00:00Z",
      is_root: true,
      is_branch_point: false,
    },
  ],
  edges: [],
};

describe("LineageDag", () => {
  it("renders an interactive graph and opens a post from click and keyboard activation", async () => {
    const user = userEvent.setup();
    const onSelectPost = vi.fn();

    render(
      <LineageDag
        graph={graph}
        onSelectPost={onSelectPost}
        currentPostId="root-post"
      />,
    );

    expect(screen.getByRole("group", { name: "synthetic-project lineage" })).toBeInTheDocument();
    expect(document.querySelectorAll(".lineage-dag-edge")).toHaveLength(1);
    expect(
      screen.getByRole("button", { name: "Open post: Root record (Current record, Root record)" }),
    ).toHaveAttribute("aria-current", "true");
    expect(document.querySelector(".lineage-list")).not.toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Open post: Child record" }));
    expect(onSelectPost).toHaveBeenLastCalledWith("child-post");

    await user.keyboard("{Enter}");
    expect(onSelectPost).toHaveBeenLastCalledWith("child-post");

    await user.keyboard(" ");
    expect(onSelectPost).toHaveBeenLastCalledWith("child-post");
    expect(onSelectPost).toHaveBeenCalledTimes(3);

    await user.keyboard("x");
    expect(onSelectPost).toHaveBeenCalledTimes(3);
  });

  it("makes direction, meaning, scrolling, and exact edge evidence accessible without hover", () => {
    render(<LineageDag graph={graph} onSelectPost={vi.fn()} currentPostId="root-post" />);

    const legend = screen.getByRole("list", { name: "Lineage legend" });
    expect(within(legend).getByText("Root record")).toBeInTheDocument();
    expect(within(legend).getByText("Branch point")).toBeInTheDocument();
    expect(within(legend).getByText("Current record")).toBeInTheDocument();
    expect(within(legend).getByText("Parent → child")).toBeInTheDocument();

    const notes = screen.getAllByRole("note");
    expect(notes.map((note) => note.textContent)).toEqual([
      "This chain has no branch point: each record matched exactly one likely predecessor. See the evidence trail below for why each link was made.",
      "Inference boundary Reconstructed edges suggest continuation; they do not prove causality or authoritative fact.",
    ]);

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
    expect(within(evidenceTable).getByText("Evidence (fused_score)")).toBeInTheDocument();
    expect(within(evidenceTable).getByText("Channel breakdown")).toBeInTheDocument();
    expect(
      within(evidenceTable).getByText("Temporal proximity 0.95 · Text similarity 0.60 · LLM judgment 0.80"),
    ).toBeInTheDocument();

    const evidenceCells = within(evidenceTable).getAllByRole("cell");
    expect(evidenceCells[0]).toHaveAttribute("data-label", "Graph relation");
    expect(evidenceCells[1]).toHaveAttribute("data-label", "When");
    expect(evidenceCells[2]).toHaveAttribute("data-label", "Evidence (fused_score)");
    expect(evidenceCells[3]).toHaveAttribute("data-label", "Channel breakdown");
  });

  it("shows the fixed channel order and falls back to the raw code for an unrecognized channel", () => {
    render(
      <LineageDag
        graph={{
          ...graph,
          edges: [
            {
              source: "root-post",
              target: "child-post",
              fused_score: 0.5,
              channel_scores: { llm: 0.4, unknown_future_channel: 0.3, temporal: 0.7 },
            },
          ],
        }}
        onSelectPost={vi.fn()}
        currentPostId="root-post"
      />,
    );

    expect(
      screen.getByText("Temporal proximity 0.70 · LLM judgment 0.40 · unknown_future_channel 0.30"),
    ).toBeInTheDocument();
  });

  it("renders an empty channel breakdown cell when no channel scores are available", () => {
    render(
      <LineageDag
        graph={{
          ...graph,
          edges: [{ source: "root-post", target: "child-post", fused_score: 0.5, channel_scores: {} }],
        }}
        onSelectPost={vi.fn()}
        currentPostId="root-post"
      />,
    );

    const evidenceTable = screen.getByRole("table", {
      name: "synthetic-project lineage — Evidence trail",
    });
    const breakdownCell = within(evidenceTable).getAllByRole("cell")[3];
    expect(breakdownCell).toHaveTextContent("");
  });

  it("keeps an isolated root interactive without rendering an empty edge table", () => {
    render(<LineageDag graph={isolatedGraph} onSelectPost={vi.fn()} />);

    expect(screen.getByRole("group", { name: "isolated-project lineage" })).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "Open post: Unlinked record (Root record)" }),
    ).toBeInTheDocument();
    expect(screen.queryByRole("table")).not.toBeInTheDocument();
    expect(screen.queryByRole("note")).not.toBeInTheDocument();
  });

  it("drops edges whose endpoints are absent from the graph", () => {
    render(
      <LineageDag
        graph={{
          ...isolatedGraph,
          edges: [{ source: "isolated-post", target: "missing-post", fused_score: 0.5, channel_scores: {} }],
        }}
        onSelectPost={vi.fn()}
      />,
    );

    expect(document.querySelector(".lineage-dag-edge")).not.toBeInTheDocument();
    expect(screen.getByRole("table")).not.toHaveTextContent("missing-post");
  });

  it("keeps long titles, Topic partitions, hierarchy, and predecessor/successor on the graph", () => {
    const multiTopic: LineageGraph = {
      nodes: [
        {
          id: "rec-001",
          group: "A-100",
          label: "Initial site visit and project scope discussion",
          occurred_at: "2026-01-01T00:00:00",
          is_root: true,
          is_branch_point: false,
        },
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
        {
          id: "rec-101",
          group: "B-200",
          label: "Technical specification review meeting",
          occurred_at: "2026-01-03T00:00:00",
          is_root: true,
          is_branch_point: false,
        },
      ],
      edges: [
        { source: "rec-001", target: "rec-002", fused_score: 0.8, channel_scores: {} },
        { source: "rec-002", target: "rec-003", fused_score: 0.9, channel_scores: {} },
        { source: "rec-002", target: "rec-004", fused_score: 0.85, channel_scores: {} },
      ],
    };

    render(<LineageDag graph={multiTopic} onSelectPost={vi.fn()} currentPostId="rec-002" />);

    const a100 = screen.getByRole("group", { name: "A-100 lineage" });
    const b200 = screen.getByRole("group", { name: "B-200 lineage" });
    expect(a100).toHaveTextContent("Initial site visit and project scope discussion");
    expect(a100).toHaveTextContent("Pricing renegotiation: revised quote sent");
    expect(a100).toHaveTextContent("Topic: A-100");
    expect(b200).toHaveTextContent("Topic: B-200");
    expect(b200).toHaveTextContent("Technical specification review meeting");
    expect(a100.textContent).not.toMatch(/…|\.\.\./);
    expect(b200.textContent).not.toMatch(/…|\.\.\./);
    expect(
      screen.getByRole("button", {
        name: "Open post: Pricing renegotiation follow-up (Current record, Branch point)",
      }),
    ).toHaveClass("lineage-dag-branch");
    expect(a100).toHaveTextContent("Root record");
    expect(a100).toHaveTextContent("Branch point");
    expect(a100).toHaveTextContent("Current record");
    expect(a100).toHaveTextContent("Earlier");
    expect(a100).toHaveTextContent("Later");
    expect(a100).toHaveTextContent("Predecessor → successor");
    expect(screen.getByRole("list", { name: "Lineage legend" })).toHaveTextContent(
      "Predecessor → successor",
    );
    const edge = document.querySelector(".lineage-dag-edge");
    expect(edge?.getAttribute("marker-end")).toMatch(/^url\(#lineage-dag-arrow-/);
    expect(a100).toHaveTextContent("2026-01-01");
    expect(a100).toHaveTextContent("2026-01-06");
    expect(a100.textContent).not.toContain("This chain has no branch point");
  });

  it("renders an actionable empty state without graph controls", () => {
    render(<LineageDag graph={{ nodes: [], edges: [] }} onSelectPost={vi.fn()} />);

    expect(
      screen.getByText(
        "No reconstructed lineage yet. Add eligible source records, then rebuild Event Lineage.",
      ),
    ).toBeInTheDocument();
    expect(screen.queryByRole("group")).not.toBeInTheDocument();
    expect(screen.queryByRole("table")).not.toBeInTheDocument();
  });
});
