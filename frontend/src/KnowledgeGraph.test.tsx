import { fireEvent, render, screen, within } from "@testing-library/react";
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
    await user.keyboard("x");
    expect(onSelectPost).toHaveBeenNthCalledWith(1, "linked-post");
    expect(onSelectPost).toHaveBeenNthCalledWith(2, "linked-post");
    expect(onSelectPost).toHaveBeenCalledTimes(2);
  });

  it("keeps malformed dangling edges in the evidence trail without drawing them", () => {
    render(
      <KnowledgeGraphView
        graph={{
          post_id: "synthetic-post",
          truncated: true,
          nodes: [
            {
              id: "target",
              node_type_code: "node_post",
              node_id: "target",
              label: "Synthetic target",
              is_focus: true,
            },
          ],
          edges: [
            {
              source: "missing-source",
              target: "target",
              edge_type_code: "related_to",
              confidence: 0.5,
              evidence_post_ids: [],
            },
          ],
        }}
      />,
    );

    expect(screen.getByText("Limited view")).toBeInTheDocument();
    expect(document.querySelector(".knowledge-graph-edge")).not.toBeInTheDocument();
    const cells = within(screen.getByRole("table")).getAllByRole("cell");
    expect(cells.map((cell) => cell.textContent)).toEqual([
      "missing-source",
      "related_to",
      "Synthetic target",
      "—",
      "50%",
    ]);
  });

  it("supports bounded zoom and keyboard/pointer panning without opening a dragged post", () => {
    const onSelectPost = vi.fn();
    const graph: KnowledgeGraph = {
      post_id: "synthetic-post",
      nodes: [
        {
          id: "post-node",
          node_type_code: "node_post",
          node_id: "linked-post",
          label: "Synthetic linked post",
          is_focus: true,
        },
      ],
      edges: [],
    };
    render(<KnowledgeGraphView graph={graph} onSelectPost={onSelectPost} />);

    const viewport = document.querySelector(".knowledge-graph-viewport") as HTMLDivElement;
    expect(viewport).not.toBeNull();
    const svg = screen.getByRole("img", { name: "Knowledge Graph directed relations" });
    vi.spyOn(svg, "getBoundingClientRect").mockReturnValue({
      x: 0,
      y: 0,
      top: 0,
      right: 760,
      bottom: 260,
      left: 0,
      width: 760,
      height: 260,
      toJSON: () => ({}),
    });
    Object.assign(viewport, {
      setPointerCapture: vi.fn(),
      hasPointerCapture: vi.fn(() => true),
      releasePointerCapture: vi.fn(),
    });

    fireEvent.keyDown(svg, { key: "ArrowLeft" });
    fireEvent.keyDown(viewport, { key: "x" });
    fireEvent.keyDown(viewport, { key: "ArrowRight" });
    expect(document.querySelector("svg > g")?.getAttribute("transform")).toContain("translate(-40 0)");

    fireEvent.wheel(viewport, { deltaY: -1, clientX: 380, clientY: 130 });
    fireEvent.wheel(viewport, { deltaY: 1, clientX: 380, clientY: 130 });
    for (let index = 0; index < 20; index += 1) {
      fireEvent.click(screen.getByRole("button", { name: "Zoom out" }));
    }
    expect(screen.getByText("75%")).toBeInTheDocument();

    const node = screen.getByRole("button", { name: "Open post: Synthetic linked post" });
    fireEvent.click(node);
    expect(onSelectPost).toHaveBeenCalledOnce();
    fireEvent.pointerDown(viewport, { button: 0, pointerId: 7, clientX: 10, clientY: 10 });
    fireEvent.pointerMove(viewport, { pointerId: 8, clientX: 30, clientY: 30 });
    fireEvent.pointerMove(viewport, { pointerId: 7, clientX: 30, clientY: 30 });
    fireEvent.pointerUp(viewport, { pointerId: 8 });
    fireEvent.pointerUp(viewport, { pointerId: 7 });
    fireEvent.click(node);
    expect(onSelectPost).toHaveBeenCalledOnce();
    expect(viewport.releasePointerCapture).toHaveBeenCalledWith(7);
  });
});
