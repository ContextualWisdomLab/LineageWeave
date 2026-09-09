import { describe, expect, it } from "vitest";
import type { OntologyNeighborhoodPayload } from "./api";
import { accumulateNeighborhoodPages, layoutOntologyNeighborhood } from "./ontologyLayout";

const POST_ID = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa1";
const PERSON_ID = "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbb1";

function payload(): OntologyNeighborhoodPayload {
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
}

describe("ontologyLayout coverage contracts", () => {
  it("drops dangling relations instead of laying out an edge with an absent endpoint", () => {
    const source = payload();
    const layout = layoutOntologyNeighborhood({
      ...source,
      edges: [
        ...source.edges,
        {
          ...source.edges[0],
          edge_id: "mentions:post-missing-person",
          target_node_id: "missing-person",
        },
      ],
    });

    expect(layout.edges.map((edge) => edge.edge_id)).toEqual(["mentions:post-person"]);
  });

  it("deduplicates a repeated voice-assignment identity in favor of the later page", () => {
    const source = payload();
    const assignment = {
      post_id: POST_ID,
      voice_type_code: "voc_customer",
      voice_type_iri: "https://example.test/voice/customer",
      voice_type_label: "Voice of Customer",
      is_primary: false,
      truth_status_code: "truth_observed",
      recorded_at: "2026-01-10T12:00:00+00:00",
      provenance_reference: "first-page evidence",
      evidence_post_id: POST_ID,
    };
    const current: OntologyNeighborhoodPayload = {
      ...source,
      voice_assignments: [assignment],
    };
    const next: OntologyNeighborhoodPayload = {
      ...source,
      voice_assignments: [
        {
          ...assignment,
          recorded_at: "2026-01-11T12:00:00+00:00",
          provenance_reference: "later-page evidence",
        },
      ],
    };

    expect(accumulateNeighborhoodPages(current, next).voice_assignments).toEqual(next.voice_assignments);
  });
});
