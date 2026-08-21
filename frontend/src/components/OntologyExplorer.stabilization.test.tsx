import { afterEach, describe, expect, it, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { OntologyNeighborhoodPayload } from "../api";
import { OntologyExplorer } from "./OntologyExplorer";

const POST_ID = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa1";
const PERSON_ID = "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbb1";

function payload(overrides: Partial<OntologyNeighborhoodPayload> = {}): OntologyNeighborhoodPayload {
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
        display_label: "Demo post",
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
        display_label: "Test person",
        truth_status_code: "truth_observed",
        valid_from: null,
        valid_to: null,
        recorded_at: "2026-01-10T12:00:00+00:00",
        evidence_count: 0,
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
        provenance_reference: "corporate_entity.parent_entity_id",
        evidence_references: [],
      },
    ],
    exact_value_rows: [
      {
        edge_id: "mentions:post-person",
        source_node_id: POST_ID,
        source_label: "Demo post",
        source_type_code: "node_post",
        property_code: "mentions",
        property_label: "mentions",
        ontology_property_iri: "https://example.test/mentions",
        target_node_id: PERSON_ID,
        target_label: "Test person",
        target_type_code: "node_person",
        truth_status_code: "truth_observed",
        recorded_at: "2026-01-10T12:00:00+00:00",
        valid_from: "",
        valid_to: "",
        evidence_count: "0",
      },
    ],
    jsonld: { "@graph": [] },
    ...overrides,
  };
}

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("OntologyExplorer stabilization contracts", () => {
  it("classifies a provided cutoff-bound payload as stale on the first render", () => {
    render(
      <OntologyExplorer
        focusNodeType="node_post"
        focusNodeId={POST_ID}
        neighborhood={payload()}
        knowledgeCutoff="2026-01-15T12:00:00Z"
      />,
    );

    expect(
      screen.getByText(
        "This neighborhood is bound to a knowledge cutoff. Compare with live evidence next.",
      ),
    ).toBeInTheDocument();
  });

  it("loads the next opaque cursor page from a truncated live neighborhood", async () => {
    const first = payload({
      truncated: true,
      next_cursor: "after:mentions:post-person",
      limitation_code: "neighborhood_truncated",
    });
    const second = payload({ truncated: false, next_cursor: null, limitation_code: null });
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce({ ok: true, status: 200, json: async () => first })
      .mockResolvedValueOnce({ ok: true, status: 200, json: async () => second });
    vi.stubGlobal("fetch", fetchMock);

    render(
      <OntologyExplorer
        accessToken="token"
        focusNodeType="node_post"
        focusNodeId={POST_ID}
      />,
    );

    expect(
      await screen.findByText(
        "Neighborhood truncated. Load the next relation page or inspect one edge.",
      ),
    ).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Load next relation page" }));

    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(2));
    expect(String(fetchMock.mock.calls[1][0])).toContain(
      "cursor=after%3Amentions%3Apost-person",
    );
  });

  it("names the next action when a hard source bound has no cursor", () => {
    render(
      <OntologyExplorer
        focusNodeType="node_post"
        focusNodeId={POST_ID}
        neighborhood={payload({
          truncated: true,
          next_cursor: null,
          limitation_code: "neighborhood_truncated",
        })}
      />,
    );

    expect(
      screen.getByText(
        "Neighborhood reached the authorized query bound. Narrow the property filter or reduce traversal depth.",
      ),
    ).toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: "Load next relation page" }),
    ).not.toBeInTheDocument();
  });

  it("does not call provenance-only edges hidden evidence", async () => {
    render(
      <OntologyExplorer
        focusNodeType="node_post"
        focusNodeId={POST_ID}
        neighborhood={payload()}
      />,
    );

    await userEvent.click(screen.getByRole("button", { name: /Select edge: mentions from/ }));
    expect(
      screen.getByText(
        "No direct evidence post is attached. Review the provenance reference above.",
      ),
    ).toBeInTheDocument();
    expect(
      screen.queryByText("Hidden evidence was removed. No omitted count is shown."),
    ).not.toBeInTheDocument();
  });
});
