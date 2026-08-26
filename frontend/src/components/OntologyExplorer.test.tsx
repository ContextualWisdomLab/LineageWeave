import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { BackendError, fetchOntologyNeighborhood } from "../api";
import type { OntologyNeighborhoodPayload } from "../api";
import { OntologyExplorer } from "./OntologyExplorer";
import { filterNeighborhood } from "../ontologyLayout";

vi.mock("../api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../api")>();
  return { ...actual, fetchOntologyNeighborhood: vi.fn() };
});

const POST_ID = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa1";
const PERSON_ID = "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbb1";
const CORP_ID = "cccccccc-cccc-cccc-cccc-ccccccccccc1";

function neighborhood(overrides: Partial<OntologyNeighborhoodPayload> = {}): OntologyNeighborhoodPayload {
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
      {
        node_id: CORP_ID,
        node_type_code: "node_corporate_entity",
        ontology_class_iri: "https://example.test/CorporateEntity",
        display_label: "Demo Corp",
        truth_status_code: "truth_observed",
        valid_from: null,
        valid_to: null,
        recorded_at: "2026-01-10T12:00:00+00:00",
        evidence_count: 1,
        shape_code: "hexagon",
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
      {
        edge_id: "affiliated:person-corp",
        source_node_type_code: "node_person",
        source_node_id: PERSON_ID,
        target_node_type_code: "node_corporate_entity",
        target_node_id: CORP_ID,
        property_code: "affiliatedWith",
        ontology_property_iri: "https://example.test/affiliatedWith",
        property_label: "affiliated with",
        truth_status_code: "truth_inferred",
        valid_from: "2026-01-01T00:00:00+00:00",
        valid_to: null,
        recorded_at: "2026-01-10T12:00:00+00:00",
        provenance_reference: "knowledge_graph_edge",
        evidence_references: [POST_ID],
      },
    ],
    exact_value_rows: [
      {
        edge_id: "mentions:post-person",
        source_node_id: POST_ID,
        source_label: "Demo public post",
        source_type_code: "node_post",
        property_code: "mentions",
        property_label: "mentions",
        ontology_property_iri: "https://example.test/mentions",
        target_node_id: PERSON_ID,
        target_label: "Test Person",
        target_type_code: "node_person",
        truth_status_code: "truth_observed",
        recorded_at: "2026-01-10T12:00:00+00:00",
        valid_from: "",
        valid_to: "",
        evidence_count: "1",
      },
      {
        edge_id: "affiliated:person-corp",
        source_node_id: PERSON_ID,
        source_label: "Test Person",
        source_type_code: "node_person",
        property_code: "affiliatedWith",
        property_label: "affiliated with",
        ontology_property_iri: "https://example.test/affiliatedWith",
        target_node_id: CORP_ID,
        target_label: "Demo Corp",
        target_type_code: "node_corporate_entity",
        truth_status_code: "truth_inferred",
        recorded_at: "2026-01-10T12:00:00+00:00",
        valid_from: "2026-01-01T00:00:00+00:00",
        valid_to: "",
        evidence_count: "1",
      },
    ],
    jsonld: { "@graph": [] },
    ...overrides,
  };
}

describe("OntologyExplorer", () => {
  it("keeps loaded pages visible when a continuation page fails", async () => {
    const fetchNeighborhood = vi.mocked(fetchOntologyNeighborhood);
    let rejectContinuation!: (error: BackendError) => void;
    fetchNeighborhood
      .mockResolvedValueOnce(neighborhood({ truncated: true, next_cursor: "page-2" }))
      .mockImplementationOnce(
        () => new Promise((_resolve, reject) => {
          rejectContinuation = reject;
        }),
      );

    render(
      <OntologyExplorer
        accessToken="synthetic-access-token"
        focusNodeType="node_post"
        focusNodeId={POST_ID}
      />,
    );

    await userEvent.click(await screen.findByRole("button", { name: "Open related item: Post Demo public post" }));
    expect(screen.getByRole("heading", { name: "Demo public post" })).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Load more related information" }));
    expect(await screen.findByText("Loading related information...")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Open related item: Post Demo public post" })).toBeInTheDocument();
    rejectContinuation(new BackendError("/api/ontology/neighborhood", 500));
    expect(await screen.findByText("Related information is unavailable. Open a visible record next.")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Open related item: Post Demo public post" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Demo public post" })).toBeInTheDocument();
    expect(fetchNeighborhood).toHaveBeenNthCalledWith(
      2,
      "synthetic-access-token",
      expect.objectContaining({ cursor: "page-2" }),
    );
  });

  it("retries a failed continuation page with the same cursor", async () => {
    const fetchNeighborhood = vi.mocked(fetchOntologyNeighborhood);
    fetchNeighborhood.mockClear();
    fetchNeighborhood
      .mockResolvedValueOnce(neighborhood({ truncated: true, next_cursor: "page-2" }))
      .mockRejectedValueOnce(new BackendError("/api/ontology/neighborhood", 500))
      .mockResolvedValueOnce(neighborhood({ next_cursor: null }));

    render(
      <OntologyExplorer
        accessToken="synthetic-access-token"
        focusNodeType="node_post"
        focusNodeId={POST_ID}
      />,
    );

    await userEvent.click(await screen.findByRole("button", { name: "Load more related information" }));
    expect(await screen.findByText("Related information is unavailable. Open a visible record next.")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Load more related information" }));
    await waitFor(() => expect(fetchNeighborhood).toHaveBeenCalledTimes(3));
    expect(screen.queryByText("Related information is unavailable. Open a visible record next.")).not.toBeInTheDocument();
    expect(fetchNeighborhood).toHaveBeenNthCalledWith(
      3,
      "synthetic-access-token",
      expect.objectContaining({ cursor: "page-2" }),
    );
  });

  it.each([403, 404])("uses one fail-closed surface for hidden and missing focus responses (%s)", async (status) => {
    const fetchNeighborhood = vi.mocked(fetchOntologyNeighborhood);
    fetchNeighborhood.mockClear();
    fetchNeighborhood.mockRejectedValueOnce(
      new BackendError("/api/ontology/neighborhood", status),
    );

    render(
      <OntologyExplorer
        accessToken="synthetic-access-token"
        focusNodeType="node_post"
        focusNodeId={POST_ID}
      />,
    );

    expect(
      await screen.findByText(
        "This information is not available. Open a visible record next.",
      ),
    ).toBeInTheDocument();
  });

  it("lets keyboard users open node and edge evidence", async () => {
    const onSelectPost = vi.fn();
    const onOpenEvidence = vi.fn();
    const payload = neighborhood();
    payload.edges[0].evidence_references = [POST_ID, "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa2"];
    render(
      <OntologyExplorer
        focusNodeType="node_post"
        focusNodeId={POST_ID}
        neighborhood={payload}
        onSelectPost={onSelectPost}
        onOpenEvidence={onOpenEvidence}
      />,
    );
    expect(
      screen.getByText(/Select a person, organization, team, or record/),
    ).toBeInTheDocument();
    expect(screen.getByRole("region", { name: "Exact values" })).toHaveAttribute("tabindex", "0");
    await userEvent.click(screen.getByRole("button", { name: "Open related item: Post Demo public post" }));
    expect(screen.getByRole("heading", { name: "Demo public post" })).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Open evidence post" }));
    expect(onSelectPost).toHaveBeenCalledWith(POST_ID);
    expect(onOpenEvidence).not.toHaveBeenCalled();
    await userEvent.click(screen.getByRole("button", { name: /Open relation: mentions from/ }));
    expect(screen.queryByText(/Property IRI/)).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Open linked record 2" })).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Open linked record 1" }));
    expect(onOpenEvidence).toHaveBeenCalledWith(POST_ID);
    expect(screen.queryByRole("img")).not.toBeInTheDocument();
  });

  it("maps known ontology node types to token-backed visual classes", () => {
    render(
      <OntologyExplorer
        focusNodeType="node_post"
        focusNodeId={POST_ID}
        neighborhood={neighborhood()}
      />,
    );

    expect(screen.getByRole("button", { name: "Open related item: Post Demo public post" }))
      .toHaveClass("ontology-node-post");
    expect(screen.getByRole("button", { name: "Open related item: Person Test Person" }))
      .toHaveClass("ontology-node-person");
    expect(screen.getByRole("button", { name: "Open related item: Organization Demo Corp" }))
      .toHaveClass("ontology-node-organization");
  });

  it("names empty, truncated, denied, and rejected next actions", () => {
    const { rerender } = render(
      <OntologyExplorer
        focusNodeType="node_post"
        focusNodeId={POST_ID}
        neighborhood={neighborhood({ edges: [], exact_value_rows: [], limitation_code: "neighborhood_empty" })}
      />,
    );
    expect(
      screen.getAllByText(
        "No related information is available. Open a record or organization next.",
      ).length,
    ).toBeGreaterThan(0);
    rerender(
      <OntologyExplorer
        focusNodeType="node_post"
        focusNodeId={POST_ID}
        neighborhood={neighborhood({ truncated: true, limitation_code: "neighborhood_truncated" })}
      />,
    );
    expect(
      screen.getByText(
        "Open a related record to review the available information.",
      ),
    ).toBeInTheDocument();
    rerender(
      <OntologyExplorer
        focusNodeType="node_post"
        focusNodeId={POST_ID}
        neighborhood={null}
        status="denied"
      />,
    );
    expect(screen.getByText("This information is not available. Open a visible record next.")).toBeInTheDocument();
    rerender(
      <OntologyExplorer
        focusNodeType="node_post"
        focusNodeId={POST_ID}
        neighborhood={neighborhood({
          edges: [{ ...neighborhood().edges[0], truth_status_code: "truth_rejected" }],
          exact_value_rows: [{ ...neighborhood().exact_value_rows[0], truth_status_code: "truth_rejected" }],
        })}
        status="rejected"
      />,
    );
    expect(screen.getByText("Rejected proposal. Open the evidence and do not treat it as authoritative.")).toBeInTheDocument();
  });

  it("does not hide rejected or cutoff warnings behind truncation", () => {
    const rejected = neighborhood({
      truncated: true,
      next_cursor: "page-2",
      edges: [{ ...neighborhood().edges[0], truth_status_code: "truth_rejected" }],
    });
    const { rerender } = render(
      <OntologyExplorer
        focusNodeType="node_post"
        focusNodeId={POST_ID}
        neighborhood={rejected}
      />,
    );
    expect(screen.getByText("Rejected proposal. Open the evidence and do not treat it as authoritative.")).toBeInTheDocument();
    expect(screen.queryByText(/Load the next relation page or inspect one edge/)).not.toBeInTheDocument();

    rerender(
      <OntologyExplorer
        focusNodeType="node_post"
        focusNodeId={POST_ID}
        neighborhood={neighborhood({ truncated: true, next_cursor: "page-2" })}
        knowledgeCutoff="2026-01-15T12:00:00Z"
      />,
    );
    expect(
      screen.getByText("Compare this information with the latest evidence before relying on it."),
    ).toBeInTheDocument();
  });

  it("does not promise paging for a static truncated neighborhood", () => {
    render(
      <OntologyExplorer
        focusNodeType="node_post"
        focusNodeId={POST_ID}
        neighborhood={neighborhood({ truncated: true, next_cursor: "page-2" })}
      />,
    );
    expect(
      screen.getByText(
        "Open a related record to review the available information.",
      ),
    ).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Load more related information" })).not.toBeInTheDocument();
  });

  it("searches the loaded graph without inventing omitted counts", async () => {
    render(
      <OntologyExplorer
        focusNodeType="node_post"
        focusNodeId={POST_ID}
        neighborhood={neighborhood()}
      />,
    );
    await userEvent.type(screen.getByLabelText("Search related information"), "Test");
    expect(screen.getAllByText("Test Person").length).toBeGreaterThan(0);
    expect(screen.queryByText(/omitted \d/i)).not.toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Reset focus" }));
    expect(screen.getByLabelText("Search related information")).toHaveValue("");
  });

  it("keeps JSON-LD aligned with the filtered graph", () => {
    const filtered = filterNeighborhood(
      neighborhood({
        jsonld: {
          "@graph": [
            { "@id": `lw:node/node_post/${POST_ID}` },
            { "@id": `lw:node/node_person/${PERSON_ID}` },
            { "@id": `lw:node/node_corporate_entity/${CORP_ID}` },
            { "@id": "lw:edge/mentions:post-person" },
            { "@id": "lw:edge/affiliated:person-corp" },
          ],
        },
      }),
      "Demo public",
    );
    const graph = filtered?.jsonld["@graph"] as Array<{ "@id": string }>;
    expect(graph.map((item) => item["@id"])).toEqual([
      `lw:node/node_post/${POST_ID}`,
      `lw:node/node_person/${PERSON_ID}`,
      "lw:edge/mentions:post-person",
    ]);
  });
});
