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
    expect(within(table).getByRole("columnheader", { name: "Category" })).toBeInTheDocument();
    expect(within(table).getByRole("columnheader", { name: "Target" })).toBeInTheDocument();
    expect(within(table).getByRole("columnheader", { name: "Evidence" })).toBeInTheDocument();
    expect(within(table).getByRole("columnheader", { name: "Confidence" })).toBeInTheDocument();

    const cells = within(table).getAllByRole("cell");
    expect(cells.map((cell) => cell.textContent)).toEqual([
      "Synthetic base release",
      "Before",
      "Time order",
      "Synthetic multi-stage release",
      "The base release came first.",
      "98%",
    ]);
    expect(document.querySelector(".knowledge-graph-edge-label")).toHaveTextContent("Before");
    expect(document.querySelector(".knowledge-graph-edge.temporal")).toBeInTheDocument();
    const legend = screen.getByRole("list", { name: "Legend" });
    expect(within(legend).getAllByRole("listitem").map((item) => item.textContent)).toEqual([
      "Time order",
      "Hierarchy",
      "Cause and effect",
      "Other relation",
    ]);
  });

  it("renders hierarchical and causal edges with their own category, table row, and edge style", () => {
    const mixedGraph: KnowledgeGraph = {
      post_id: "synthetic-post",
      nodes: [
        { id: "plant", node_type_code: "node_corporate_entity", node_id: "plant", label: "Plant", is_focus: false },
        { id: "company", node_type_code: "node_corporate_entity", node_id: "company", label: "Company", is_focus: false },
        { id: "delay", node_type_code: "semantic_event", node_id: "delay", label: "Permit delay", is_focus: false },
        { id: "slip", node_type_code: "semantic_event", node_id: "slip", label: "Schedule slip", is_focus: false },
      ],
      edges: [
        {
          source: "plant",
          target: "company",
          edge_type_code: "org_suborganization_of",
          ontology_label: "Sub-organization of",
          confidence: 0.95,
          evidence_post_ids: ["synthetic-post"],
        },
        {
          source: "delay",
          target: "slip",
          edge_type_code: "lw_has_consequence",
          ontology_label: "Has consequence",
          confidence: 0.85,
          evidence_post_ids: ["synthetic-post"],
        },
      ],
    };
    render(<KnowledgeGraphView graph={mixedGraph} />);

    const table = screen.getByRole("table", { name: "Knowledge Graph — Evidence trail" });
    const rows = within(table).getAllByRole("row").slice(1);
    expect(rows.map((row) => within(row).getAllByRole("cell").map((cell) => cell.textContent))).toEqual([
      ["Plant", "Sub-organization of", "Hierarchy", "Company", "—", "95%"],
      ["Permit delay", "Has consequence", "Cause and effect", "Schedule slip", "—", "85%"],
    ]);
    expect(document.querySelector(".knowledge-graph-edge.hierarchical")).toBeInTheDocument();
    expect(document.querySelector(".knowledge-graph-edge.causal")).toBeInTheDocument();
  });

  it("orders nodes by temporal precedence instead of raw array position", () => {
    // Declared out of chronological order (C, A, D, B) to prove layout
    // ordering follows the time_before chain A -> B -> C -> D, not the
    // order the nodes happen to appear in the API payload.
    const chain: KnowledgeGraph = {
      post_id: "synthetic-post",
      nodes: [
        { id: "c", node_type_code: "semantic_temporal_entity", node_id: "c", label: "Stage C", is_focus: false },
        { id: "a", node_type_code: "semantic_temporal_entity", node_id: "a", label: "Stage A", is_focus: false },
        { id: "d", node_type_code: "semantic_temporal_entity", node_id: "d", label: "Stage D", is_focus: false },
        { id: "b", node_type_code: "semantic_temporal_entity", node_id: "b", label: "Stage B", is_focus: false },
      ],
      edges: [
        { source: "a", target: "b", edge_type_code: "time_before", confidence: 0.9, evidence_post_ids: [] },
        { source: "b", target: "c", edge_type_code: "time_before", confidence: 0.9, evidence_post_ids: [] },
        { source: "c", target: "d", edge_type_code: "time_before", confidence: 0.9, evidence_post_ids: [] },
      ],
    };
    render(<KnowledgeGraphView graph={chain} />);

    const yOf = (label: string) => {
      const group = [...document.querySelectorAll(".knowledge-graph-node")].find(
        (candidate) => candidate.querySelector("title")?.textContent === label,
      );
      const transform = group?.getAttribute("transform") ?? "";
      const match = transform.match(/translate\([^,]+,\s*([\d.]+)\)/);
      return Number(match?.[1]);
    };

    const yA = yOf("Stage A");
    const yB = yOf("Stage B");
    const yC = yOf("Stage C");
    const yD = yOf("Stage D");
    // Two per row (see layoutKnowledgeGraph): A and B share the top row,
    // C and D share the next row down -- so the chain renders top-to-bottom
    // in chronological order even though the payload listed C, A, D, B.
    expect(yA).toBe(yB);
    expect(yC).toBe(yD);
    expect(yA).toBeLessThan(yC);
  });

  it("orders nodes by hierarchical precedence, a reverse-direction predicate, the same way", () => {
    // org_suborganization_of(child, parent) uses "reverse" in ORDER_DIRECTION
    // (the target precedes the source) -- declared child-before-parent here
    // to prove the reverse branch renders the parent above the child through
    // the full component, not just in the isolated precedenceFromEdges unit
    // test.
    const hierarchy: KnowledgeGraph = {
      post_id: "synthetic-post",
      nodes: [
        { id: "plant", node_type_code: "node_corporate_entity", node_id: "plant", label: "Plant", is_focus: false },
        { id: "company", node_type_code: "node_corporate_entity", node_id: "company", label: "Company", is_focus: false },
        { id: "group", node_type_code: "node_corporate_entity", node_id: "group", label: "Group", is_focus: false },
      ],
      edges: [
        {
          source: "plant",
          target: "company",
          edge_type_code: "org_suborganization_of",
          confidence: 0.9,
          evidence_post_ids: [],
        },
        {
          source: "company",
          target: "group",
          edge_type_code: "org_suborganization_of",
          confidence: 0.9,
          evidence_post_ids: [],
        },
      ],
    };
    render(<KnowledgeGraphView graph={hierarchy} />);

    const yOf = (label: string) => {
      const group = [...document.querySelectorAll(".knowledge-graph-node")].find(
        (candidate) => candidate.querySelector("title")?.textContent === label,
      );
      const transform = group?.getAttribute("transform") ?? "";
      const match = transform.match(/translate\([^,]+,\s*([\d.]+)\)/);
      return Number(match?.[1]);
    };

    // Three nodes lay out two-per-row: group (broadest) and company share
    // the top row, plant (narrowest) is alone on the row below.
    expect(yOf("Group")).toBe(yOf("Company"));
    expect(yOf("Group")).toBeLessThan(yOf("Plant"));
  });

  it("never lets a precedence edge touching the focus node reorder unrelated siblings", () => {
    // The focus node is excluded from the id set topologicalOrder operates
    // over. Before the fix, a classified predicate touching focus (here,
    // focus --time_before--> a) seeded an indegree on "a" that could never
    // be released, shoving it to the end of the layout ahead of b/c even
    // though it has no real precedence relation to either of them.
    const graph: KnowledgeGraph = {
      post_id: "synthetic-post",
      nodes: [
        { id: "focus", node_type_code: "node_post", node_id: "synthetic-post", label: "Focus post", is_focus: true },
        { id: "a", node_type_code: "semantic_event", node_id: "a", label: "Node A", is_focus: false },
        { id: "b", node_type_code: "semantic_event", node_id: "b", label: "Node B", is_focus: false },
        { id: "c", node_type_code: "semantic_event", node_id: "c", label: "Node C", is_focus: false },
      ],
      edges: [
        { source: "focus", target: "a", edge_type_code: "time_before", confidence: 0.9, evidence_post_ids: [] },
      ],
    };
    render(<KnowledgeGraphView graph={graph} />);

    const yOf = (label: string) => {
      const group = [...document.querySelectorAll(".knowledge-graph-node")].find(
        (candidate) => candidate.querySelector("title")?.textContent === label,
      );
      const transform = group?.getAttribute("transform") ?? "";
      const match = transform.match(/translate\([^,]+,\s*([\d.]+)\)/);
      return Number(match?.[1]);
    };

    // a/b share the top row, c the next row down -- original array order
    // (a, b, c) preserved, not reshuffled by the focus-incident edge.
    expect(yOf("Node A")).toBe(yOf("Node B"));
    expect(yOf("Node A")).toBeLessThan(yOf("Node C"));
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
        {
          source: "focus",
          target: "later",
          edge_type_code: "synthetic_relation",
          confidence: 0.75,
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
    await user.click(screen.getByRole("button", { name: "Zoom in" }));
    expect(screen.getByText("120%")).toBeInTheDocument();
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
            {
              id: "evidence",
              node_type_code: "evidence_text",
              node_id: "evidence",
              label: "Synthetic evidence",
              ontology_label: null,
              is_focus: false,
              is_evidence_text_node: true,
            },
          ],
          edges: [
            {
              source: "missing-source",
              target: "missing-target",
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
      "Other relation",
      "missing-target",
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
    const hasPointerCapture = vi.fn().mockReturnValueOnce(true).mockReturnValueOnce(false);
    Object.assign(viewport, {
      setPointerCapture: vi.fn(),
      hasPointerCapture,
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
    fireEvent.pointerMove(viewport, { pointerId: 7, clientX: 20, clientY: 20 });
    fireEvent.pointerDown(viewport, { button: 1, pointerId: 7, clientX: 10, clientY: 10 });
    fireEvent.pointerDown(viewport, { button: 0, pointerId: 7, clientX: 10, clientY: 10 });
    fireEvent.pointerMove(viewport, { pointerId: 7, clientX: 10, clientY: 10 });
    fireEvent.pointerMove(viewport, { pointerId: 8, clientX: 30, clientY: 30 });
    fireEvent.pointerMove(viewport, { pointerId: 7, clientX: 30, clientY: 30 });
    fireEvent.pointerUp(viewport, { pointerId: 8 });
    fireEvent.pointerUp(viewport, { pointerId: 7 });
    fireEvent.pointerUp(viewport, { pointerId: 7 });
    fireEvent.pointerDown(viewport, { button: 0, pointerId: 9, clientX: 10, clientY: 10 });
    fireEvent.pointerUp(viewport, { pointerId: 9 });
    fireEvent.click(node);
    expect(onSelectPost).toHaveBeenCalledOnce();
    expect(viewport.releasePointerCapture).toHaveBeenCalledWith(7);
  });
});
