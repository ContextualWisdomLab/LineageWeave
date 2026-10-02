import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import type { OntologyNeighborhoodPayload } from "../api";
import { OntologyExplorer } from "./OntologyExplorer";

const POST_ID = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa1";
const CUSTOM_ID = "dddddddd-dddd-dddd-dddd-ddddddddddd1";
const MISSING_EVIDENCE_POST_ID = "eeeeeeee-eeee-eeee-eeee-eeeeeeeeeee1";

function extensionNeighborhood(): OntologyNeighborhoodPayload {
  return {
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
        display_label: "Public post",
        truth_status_code: "truth_observed",
        valid_from: null,
        valid_to: null,
        recorded_at: "2026-09-16T00:00:00+00:00",
        evidence_count: 1,
        shape_code: "rectangle",
      },
      {
        node_id: CUSTOM_ID,
        node_type_code: "node_external_record",
        ontology_class_iri: "https://example.test/ExternalRecord",
        display_label: "External record",
        truth_status_code: null,
        valid_from: null,
        valid_to: null,
        recorded_at: null,
        evidence_count: 0,
        shape_code: "rectangle",
      },
    ],
    edges: [
      {
        edge_id: "external:post-record",
        source_node_type_code: "node_post",
        source_node_id: POST_ID,
        target_node_type_code: "node_external_record",
        target_node_id: CUSTOM_ID,
        property_code: "referencesExternalRecord",
        ontology_property_iri: "https://example.test/referencesExternalRecord",
        property_label: "references external record",
        truth_status_code: "truth_external",
        valid_from: null,
        valid_to: null,
        recorded_at: "2026-09-16T00:00:00+00:00",
        provenance_reference: "external_extension_contract",
        evidence_references: [],
      },
    ],
    exact_value_rows: [
      {
        edge_id: "voice:post-customer",
        source_node_id: POST_ID,
        source_label: "Public post",
        source_type_code: "node_post",
        property_code: "hasVoiceAssignment",
        property_label: "Voice carried by this post",
        ontology_property_iri: "https://example.test/hasVoiceAssignment",
        target_node_id: "voc_customer",
        target_label: "Voice of Customer",
        target_type_code: "node_voice_type",
        truth_status_code: "truth_external",
        recorded_at: "2026-09-16T00:00:00+00:00",
        valid_from: "",
        valid_to: "",
        evidence_count: "1",
        evidence_post_id: MISSING_EVIDENCE_POST_ID,
      },
    ],
    jsonld: { "@graph": [] },
  };
}

describe("OntologyExplorer extension fallbacks", () => {
  it("keeps unknown node and truth codes visible instead of dropping extension evidence", async () => {
    const onSelectPost = vi.fn();
    render(
      <OntologyExplorer
        focusNodeType="node_post"
        focusNodeId={POST_ID}
        neighborhood={extensionNeighborhood()}
        onSelectPost={onSelectPost}
      />,
    );

    const customNode = screen.getByRole("button", {
      name: "Select node: node_external_record External record",
    });
    expect(customNode).toHaveClass("ontology-node-generic");
    expect(screen.getAllByText("truth_external").length).toBeGreaterThan(0);

    await userEvent.click(customNode);
    expect(screen.getByRole("heading", { name: "External record" })).toBeInTheDocument();
    expect(screen.getByText(/node_external_record · Unknown/)).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Focus this node next" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Open evidence post" })).not.toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Close record details" }));

    await userEvent.click(
      screen.getByRole("button", { name: `Open evidence: ${MISSING_EVIDENCE_POST_ID}` }),
    );
    expect(onSelectPost).toHaveBeenCalledWith(MISSING_EVIDENCE_POST_ID);
  });

  it("falls back to the evidence callback when the carrying-post callback is absent", async () => {
    const onOpenEvidence = vi.fn();
    render(
      <OntologyExplorer
        focusNodeType="node_post"
        focusNodeId={POST_ID}
        neighborhood={extensionNeighborhood()}
        onOpenEvidence={onOpenEvidence}
      />,
    );

    await userEvent.click(screen.getByRole("button", { name: "Open post: Public post" }));
    expect(onOpenEvidence).toHaveBeenCalledWith(POST_ID);

    const edge = screen.getByRole("button", { name: /Select edge: references external record from/ });
    edge.focus();
    await userEvent.keyboard("{Enter}");
    expect(screen.getByRole("heading", { name: "references external record" })).toBeInTheDocument();
    expect(
      screen.getByText("No direct evidence post is attached. Review the provenance reference above."),
    ).toBeInTheDocument();
  });
});
