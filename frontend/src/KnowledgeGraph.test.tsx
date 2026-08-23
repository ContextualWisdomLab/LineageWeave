import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import type { KnowledgeGraph } from "./api";
import { KnowledgeGraphView } from "./KnowledgeGraph";

const directedTemporalGraph: KnowledgeGraph = {
  post_id: "synthetic-post",
  nodes: [
    {
      id: "earlier",
      node_type_code: "semantic_temporal_entity",
      node_id: "earlier",
      label: "Synthetic base release",
      ontology_label: "temporal_entity",
      is_focus: false,
      is_evidence_text_node: true,
    },
    {
      id: "later",
      node_type_code: "semantic_temporal_entity",
      node_id: "later",
      label: "Synthetic multi-stage release",
      ontology_label: "temporal_entity",
      is_focus: false,
      is_evidence_text_node: true,
    },
  ],
  edges: [
    {
      source: "earlier",
      target: "later",
      edge_type_code: "time_before",
      ontology_label: "Before",
      confidence: 0.98,
      evidence_text: "The base release came first.",
      evidence_post_ids: ["synthetic-post"],
    },
  ],
};

describe("KnowledgeGraphView", () => {
  it("makes directed semantic relations understandable without hover", () => {
    render(<KnowledgeGraphView graph={directedTemporalGraph} />);

    expect(screen.getByText(/source → target/, { selector: "p" })).toHaveTextContent(
      "Arrows show source → target; use arrow keys to pan and controls to zoom.",
    );
    expect(screen.getByRole("group", { name: "Graph controls" })).toBeInTheDocument();
    expect(screen.getByRole("img", { name: "Knowledge Graph directed relations" })).toBeInTheDocument();

    const table = screen.getByRole("table", { name: "Knowledge Graph — Evidence trail" });
    expect(within(table).getByRole("columnheader", { name: "Source" })).toBeInTheDocument();
    expect(within(table).getByRole("columnheader", { name: "Relation" })).toBeInTheDocument();
    expect(within(table).getByRole("columnheader", { name: "Target" })).toBeInTheDocument();
    expect(within(table).getByRole("columnheader", { name: "Evidence" })).toBeInTheDocument();
    expect(within(table).getByRole("columnheader", { name: "Confidence" })).toBeInTheDocument();

    const cells = within(table).getAllByRole("cell");
    expect(cells.map((cell) => cell.textContent)).toEqual([
      "Synthetic base release",
      "Before",
      "Synthetic multi-stage release",
      "The base release came first.",
      "98%",
    ]);
    expect(document.querySelector(".knowledge-graph-edge-label")).toHaveTextContent("Before");
  });

  it("keeps long node and relation titles on the graph without ellipsis", () => {
    const longLabelGraph: KnowledgeGraph = {
      post_id: "synthetic-post",
      nodes: [
        {
          id: "focus",
          node_type_code: "node_post",
          node_id: "synthetic-post",
          label: "Initial site visit and project scope discussion",
          ontology_label: "Post",
          is_focus: true,
        },
        {
          id: "later",
          node_type_code: "semantic_temporal_entity",
          node_id: "later",
          label: "Pricing renegotiation: revised quote sent",
          ontology_label: "temporal_entity",
          is_focus: false,
          is_evidence_text_node: true,
        },
      ],
      edges: [
        {
          source: "focus",
          target: "later",
          edge_type_code: "time_before",
          ontology_label: "mentioned in reconstructed continuation",
          confidence: 0.91,
          evidence_text: "The site visit came first.",
          evidence_post_ids: ["synthetic-post"],
        },
      ],
    };

    render(<KnowledgeGraphView graph={longLabelGraph} />);

    const svg = screen.getByRole("img", { name: "Knowledge Graph directed relations" });
    expect(svg).toHaveTextContent("Initial site visit and project scope discussion");
    expect(svg).toHaveTextContent("Pricing renegotiation: revised quote sent");
    expect(svg).toHaveTextContent("mentioned in reconstructed continuation");
    expect(svg.textContent).not.toMatch(/…/);
    expect(document.querySelector(".knowledge-graph-edge path")?.getAttribute("marker-end")).toMatch(
      /knowledge-graph-arrow/,
    );
  });

  it("keeps zoom controls operable and omits the graph table for an empty state", async () => {
    const user = userEvent.setup();
    const { rerender } = render(<KnowledgeGraphView graph={directedTemporalGraph} />);

    await user.click(screen.getByRole("button", { name: "Zoom in" }));
    expect(screen.getByText("120%")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Reset graph view" }));
    expect(screen.getByText("100%")).toBeInTheDocument();

    rerender(<KnowledgeGraphView graph={{ post_id: "synthetic-post", nodes: [], edges: [] }} />);
    expect(screen.getByText("No Knowledge Graph evidence is available.")).toBeInTheDocument();
    expect(screen.queryByRole("table")).not.toBeInTheDocument();
  });

  it("opens post nodes with keyboard activation", async () => {
    const onSelectPost = vi.fn();
    const graph: KnowledgeGraph = {
      post_id: "synthetic-post",
      nodes: [
        {
          id: "post-node",
          node_type_code: "node_post",
          node_id: "linked-post",
          label: "Synthetic linked post",
          is_focus: false,
        },
      ],
      edges: [],
    };
    const user = userEvent.setup();
    render(<KnowledgeGraphView graph={graph} onSelectPost={onSelectPost} />);

    const node = screen.getByRole("button", { name: "Open post: Synthetic linked post" });
    node.focus();
    await user.keyboard("{Enter}");
    await user.keyboard(" ");
    expect(onSelectPost).toHaveBeenNthCalledWith(1, "linked-post");
    expect(onSelectPost).toHaveBeenNthCalledWith(2, "linked-post");
  });
});
