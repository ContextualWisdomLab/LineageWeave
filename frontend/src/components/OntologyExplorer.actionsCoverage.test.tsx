import { fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
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

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("OntologyExplorer buyer actions", () => {
  it("prints, closes disclosures, and preserves evidence callback fallbacks", () => {
    const print = vi.fn();
    const onOpenEvidence = vi.fn();
    const onSelectPost = vi.fn();
    vi.stubGlobal("print", print);

    const { rerender } = render(
      <OntologyExplorer
        focusNodeType="node_post"
        focusNodeId={POST_ID}
        neighborhood={neighborhood}
        onOpenEvidence={onOpenEvidence}
      />,
    );

    fireEvent.click(screen.getByRole("button", { name: "Print this neighborhood" }));
    expect(print).toHaveBeenCalledTimes(1);

    fireEvent.click(screen.getByRole("button", { name: "Select node: Post Demo public post" }));
    expect(screen.getByLabelText("Node evidence")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Open evidence post" }));
    expect(onOpenEvidence).toHaveBeenCalledWith(POST_ID);
    fireEvent.click(screen.getByRole("button", { name: "Close record details" }));
    expect(screen.queryByLabelText("Node evidence")).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: /Select edge: mentions from/ }));
    expect(screen.getByLabelText("Edge provenance")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: /Open evidence:/ }));
    expect(onOpenEvidence).toHaveBeenLastCalledWith(POST_ID);
    fireEvent.click(screen.getByRole("button", { name: "Close record details" }));
    expect(screen.queryByLabelText("Edge provenance")).not.toBeInTheDocument();

    rerender(
      <OntologyExplorer
        focusNodeType="node_post"
        focusNodeId={POST_ID}
        neighborhood={neighborhood}
        onSelectPost={onSelectPost}
      />,
    );
    fireEvent.click(screen.getByRole("button", { name: /Select edge: mentions from/ }));
    fireEvent.click(screen.getByRole("button", { name: /Open evidence:/ }));
    expect(onSelectPost).toHaveBeenCalledWith(POST_ID);
  });
});
