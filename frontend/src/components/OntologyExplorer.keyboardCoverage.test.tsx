import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import type { OntologyNeighborhoodPayload } from "../api";
import { OntologyExplorer } from "./OntologyExplorer";

const POST_ID = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa1";
const PERSON_ID = "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbb1";

const neighborhood: OntologyNeighborhoodPayload = {
  focus_node_id: POST_ID,
  focus_node_type_code: "node_post",
  truncated: false,
  next_cursor: null,
  limitation_code: null,
  nodes: [
    {
      node_id: POST_ID,
      node_type_code: "node_post",
      ontology_class_iri: "https://example.test/Post",
      display_label: "Demo public post",
      truth_status_code: "truth_observed",
      valid_from: null,
      valid_to: null,
      recorded_at: "2026-01-10T12:00:00+00:00",
      evidence_count: 1,
      shape_code: "rectangle",
    },
    {
      node_id: PERSON_ID,
      node_type_code: "node_person",
      ontology_class_iri: "https://example.test/Person",
      display_label: "Test Person",
      truth_status_code: "truth_observed",
      valid_from: null,
      valid_to: null,
      recorded_at: "2026-01-10T12:00:00+00:00",
      evidence_count: 1,
      shape_code: "ellipse",
    },
  ],
  edges: [
    {
      edge_id: "mentions:post-person",
      source_node_type_code: "node_post",
      source_node_id: POST_ID,
      target_node_type_code: "node_person",
      target_node_id: PERSON_ID,
      property_code: "mentions",
      ontology_property_iri: "https://example.test/mentions",
      property_label: "mentions",
      truth_status_code: "truth_observed",
      valid_from: null,
      valid_to: null,
      recorded_at: "2026-01-10T12:00:00+00:00",
      provenance_reference: "knowledge_graph_edge",
      evidence_references: [POST_ID],
    },
  ],
  exact_value_rows: [],
  jsonld: { "@graph": [] },
};

describe("OntologyExplorer graph keyboard selection", () => {
  it("keeps edge and node selection operable through focus, Enter, and Space", () => {
    render(
      <OntologyExplorer
        focusNodeType="node_post"
        focusNodeId={POST_ID}
        neighborhood={neighborhood}
      />,
    );

    const edge = screen.getByRole("button", { name: /Select edge: mentions from/ });
    edge.focus();
    expect(edge).toHaveFocus();
    expect(edge).toHaveAttribute("aria-pressed", "false");

    fireEvent.keyDown(edge, { key: "Escape" });
    expect(edge).toHaveAttribute("aria-pressed", "false");

    fireEvent.keyDown(edge, { key: "Enter" });
    expect(edge).toHaveAttribute("aria-pressed", "true");
    expect(screen.getByText(/Property IRI/)).toBeInTheDocument();

    fireEvent.keyDown(edge, { key: " " });
    expect(edge).toHaveAttribute("aria-pressed", "true");

    let node = screen.getByRole("button", { name: "Select node: Post Demo public post" });
    node.focus();
    expect(node).toHaveFocus();
    expect(node).toHaveAttribute("aria-pressed", "false");

    fireEvent.keyDown(node, { key: "Escape" });
    expect(node).toHaveAttribute("aria-pressed", "false");

    fireEvent.keyDown(node, { key: " " });
    node = screen.getByRole("button", { name: "Select node: Post Demo public post" });
    expect(node).toHaveAttribute("aria-pressed", "true");
    expect(screen.getByRole("heading", { name: "Demo public post" })).toBeInTheDocument();

    fireEvent.keyDown(node, { key: "Enter" });
    expect(
      screen.getByRole("button", { name: "Select node: Post Demo public post" }),
    ).toHaveAttribute("aria-pressed", "true");
  });
});
