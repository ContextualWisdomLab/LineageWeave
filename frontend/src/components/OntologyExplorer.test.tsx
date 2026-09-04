import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { BackendError, fetchOntologyNeighborhood } from "../api";
import type { OntologyNeighborhoodPayload } from "../api";
import { OntologyExplorer } from "./OntologyExplorer";
import { filterNeighborhood } from "../ontologyLayout";

vi.mock("../api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../api")>();
  return { ...actual, fetchOntologyNeighborhood: vi.fn(), fetchOccupationalConstructSearch: vi.fn() };
});

const POST_ID = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa1";
const EVIDENCE_POST_ID = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa2";
const PERSON_ID = "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbb1";
const CORP_ID = "cccccccc-cccc-cccc-cccc-ccccccccccc1";
const CONSTRUCT_ID = "99999999-9999-9999-9999-999999999999";

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
  it("keeps the exact-value heading outside the focusable horizontal scroller", () => {
    const { container } = render(
      <OntologyExplorer
        focusNodeType="node_post"
        focusNodeId={POST_ID}
        neighborhood={neighborhood()}
      />,
    );

    const region = screen.getByRole("region", { name: "Exact values" });
    const heading = screen.getByRole("heading", { name: "Exact values" });
    const scroller = container.querySelector(".ontology-exact-values-scroll");
    expect(region).toContainElement(heading);
    expect(scroller).toHaveAttribute("tabindex", "0");
    expect(scroller).toContainElement(screen.getByRole("table", { name: "Exact values" }));
    expect(scroller).not.toContainElement(heading);
  });

  it("renders a project node with a text-labeled diamond", () => {
    const payload = neighborhood();
    const projectNode = {
      ...payload.nodes[0],
      node_id: `${POST_ID}/demo-project`,
      node_type_code: "node_project",
      ontology_class_iri: "https://example.test/Project",
      display_label: "Demo Project",
      truth_status_code: "truth_proposed",
      shape_code: "diamond",
    };
    const { container } = render(
      <OntologyExplorer
        focusNodeType="node_project"
        focusNodeId={`${POST_ID}/demo-project`}
        neighborhood={{ ...payload, nodes: [projectNode], edges: [], exact_value_rows: [] }}
      />,
    );

    expect(screen.getByLabelText("Select node: Project Demo Project")).toBeVisible();
    expect(container.querySelector('polygon[points="0,-16 20,0 0,16 -20,0"]')).not.toBeNull();
  });

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

    await userEvent.click(await screen.findByRole("button", { name: "Select node: Post Demo public post" }));
    expect(screen.getByRole("heading", { name: "Demo public post" })).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Load next relation page" }));
    expect(await screen.findByText("Loading related information...")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Select node: Post Demo public post" })).toBeInTheDocument();
    rejectContinuation(new BackendError("/api/ontology/neighborhood", 500));
    expect(await screen.findByText("Related information is unavailable. Open a visible post next.")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Select node: Post Demo public post" })).toBeInTheDocument();
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

    await userEvent.click(await screen.findByRole("button", { name: "Load next relation page" }));
    expect(await screen.findByText("Related information is unavailable. Open a visible post next.")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Load next relation page" }));
    await waitFor(() => expect(fetchNeighborhood).toHaveBeenCalledTimes(3));
    expect(screen.queryByText("Related information is unavailable. Open a visible post next.")).not.toBeInTheDocument();
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
        "Related information is unavailable for this record. Open a visible post next.",
      ),
    ).toBeInTheDocument();
  });

  it("lets keyboard users open node and edge evidence", async () => {
    const onSelectPost = vi.fn();
    const onOpenEvidence = vi.fn();
    render(
      <OntologyExplorer
        focusNodeType="node_post"
        focusNodeId={POST_ID}
        neighborhood={neighborhood()}
        onSelectPost={onSelectPost}
        onOpenEvidence={onOpenEvidence}
      />,
    );
    expect(
      screen.getByText("Review related records and open a source post for details."),
    ).toBeInTheDocument();
    expect(screen.getByRole("columnheader", { name: "Valid from" })).toBeInTheDocument();
    expect(screen.getByRole("columnheader", { name: "Valid to" })).toBeInTheDocument();
    expect(screen.getByRole("columnheader", { name: "Evidence" })).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Select node: Post Demo public post" }));
    expect(screen.getByRole("heading", { name: "Demo public post" })).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Open evidence post" }));
    expect(onSelectPost).toHaveBeenCalledWith(POST_ID);
    expect(onOpenEvidence).not.toHaveBeenCalled();
    await userEvent.click(screen.getByRole("button", { name: /Select edge: mentions from/ }));
    expect(screen.getByText(/Property IRI/)).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: `Open evidence: ${POST_ID}` }));
    expect(onOpenEvidence).toHaveBeenCalledWith(POST_ID);
    expect(screen.queryByRole("img")).not.toBeInTheDocument();
  });

  it("opens the carrying post and its authorized Voice evidence separately", async () => {
    const onOpenEvidence = vi.fn();
    const onSelectPost = vi.fn();
    const source = neighborhood();
    render(
      <OntologyExplorer
        focusNodeType="node_post"
        focusNodeId={POST_ID}
        neighborhood={{
          ...source,
          voice_assignments: [
            {
              post_id: POST_ID,
              voice_type_code: "voc_customer",
              voice_type_iri: "https://example.test/voice/customer",
              voice_type_label: "Voice of Customer",
              is_primary: false,
              truth_status_code: "truth_observed",
              recorded_at: "2026-01-10T12:00:00+00:00",
              provenance_reference: "prov:assignment",
              evidence_post_id: EVIDENCE_POST_ID,
            },
          ],
          exact_value_rows: [
            ...source.exact_value_rows,
            {
              ...source.exact_value_rows[0],
              edge_id: `voice-assignment:${POST_ID}:voc_customer`,
              property_code: "hasVoiceAssignment",
              property_label: "Voice carried by this post",
              target_node_id: "voc_customer",
              target_label: "Voice of Customer",
              target_type_code: "node_voice_type",
              evidence_post_id: EVIDENCE_POST_ID,
            },
          ],
          nodes: [
            ...source.nodes,
            {
              ...source.nodes[0],
              node_id: EVIDENCE_POST_ID,
              display_label: "Demo evidence post",
            },
          ],
        }}
        onSelectPost={onSelectPost}
        onOpenEvidence={onOpenEvidence}
      />,
    );

    await userEvent.click(
      screen.getByRole("button", { name: "Open post: Demo public post" }),
    );
    expect(onSelectPost).toHaveBeenCalledWith(POST_ID);
    await userEvent.click(screen.getByRole("button", { name: "Open evidence: Demo evidence post" }));
    expect(onOpenEvidence).toHaveBeenCalledWith(EVIDENCE_POST_ID);
  });

  it("does not present imported primary source evidence as derivation evidence", () => {
    const source = neighborhood();
    render(
      <OntologyExplorer
        focusNodeType="node_post"
        focusNodeId={POST_ID}
        neighborhood={{
          ...source,
          voice_assignments: [
            {
              post_id: POST_ID,
              voice_type_code: "voc_customer",
              voice_type_iri: "https://example.test/voice/customer",
              voice_type_label: "Voice of Customer",
              is_primary: true,
              truth_status_code: "truth_observed",
              recorded_at: "2026-01-10T12:00:00+00:00",
              provenance_reference: "Imported primary voice",
              evidence_post_id: POST_ID,
            },
          ],
          exact_value_rows: [
            {
              ...source.exact_value_rows[0],
              edge_id: `voice-assignment:${POST_ID}:voc_customer`,
              property_code: "hasVoiceAssignment",
              property_label: "Voice carried by this post",
              target_node_id: "voc_customer",
              target_label: "Voice of Customer",
              target_type_code: "node_voice_type",
              evidence_post_id: POST_ID,
            },
          ],
        }}
      />,
    );

    expect(screen.getByRole("button", { name: "Open post: Demo public post" })).toBeVisible();
    expect(screen.queryByRole("button", { name: "Open evidence: Demo public post" })).not.toBeInTheDocument();
  });

  it("keeps complete long node labels in the rendered graph and exact-value table", () => {
    const longLabel =
      "Synthetic multilingual procurement governance decision with complete provenance";
    const payload = neighborhood({
      nodes: neighborhood().nodes.map((node, index) =>
        index === 0 ? { ...node, display_label: longLabel } : node,
      ),
      exact_value_rows: neighborhood().exact_value_rows.map((row, index) =>
        index === 0 ? { ...row, source_label: longLabel } : row,
      ),
    });
    render(
      <OntologyExplorer
        focusNodeType="node_post"
        focusNodeId={POST_ID}
        neighborhood={payload}
      />,
    );

    expect(screen.getAllByText(longLabel)).toHaveLength(2);
    expect(screen.getByRole("button", { name: `Select node: Post ${longLabel}` })).toBeInTheDocument();
  });

  it("maps known ontology node types to token-backed visual classes", () => {
    const payload = neighborhood();
    const projectNode = {
      ...payload.nodes[0],
      node_id: `${POST_ID}/demo-project`,
      node_type_code: "node_project",
      ontology_class_iri: "https://example.test/Project",
      display_label: "Demo Project",
      truth_status_code: "truth_proposed",
      shape_code: "diamond",
    };
    render(
      <OntologyExplorer
        focusNodeType="node_post"
        focusNodeId={POST_ID}
        neighborhood={{ ...payload, nodes: [...payload.nodes, projectNode] }}
      />,
    );

    expect(screen.getByRole("button", { name: "Select node: Post Demo public post" }))
      .toHaveClass("ontology-node-post");
    expect(screen.getByRole("button", { name: "Select node: Person Test Person" }))
      .toHaveClass("ontology-node-person");
    expect(screen.getByRole("button", { name: "Select node: Organization Demo Corp" }))
      .toHaveClass("ontology-node-organization");
    expect(screen.getByRole("button", { name: "Select node: Project Demo Project" }))
      .toHaveClass("ontology-node-project");
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
        "No related information is available. Open a visible post next.",
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
        "Neighborhood reached the authorized query bound. Narrow the property filter or reduce traversal depth.",
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
    expect(screen.getByText("Related information is unavailable for this record. Open a visible post next.")).toBeInTheDocument();
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
    expect(screen.getByText("This suggestion was not accepted. Open the evidence to review it.")).toBeInTheDocument();
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
    expect(screen.getByText("This suggestion was not accepted. Open the evidence to review it.")).toBeInTheDocument();
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
      screen.getByText("This information reflects an earlier view. Compare it with the current record next."),
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
        "Neighborhood reached the authorized query bound. Narrow the property filter or reduce traversal depth.",
      ),
    ).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Load next relation page" })).not.toBeInTheDocument();
  });

  it("searches the loaded graph without inventing omitted counts", async () => {
    render(
      <OntologyExplorer
        focusNodeType="node_post"
        focusNodeId={POST_ID}
        neighborhood={neighborhood()}
      />,
    );
    await userEvent.type(screen.getByLabelText("Search within this neighborhood"), "Test");
    expect(screen.getAllByText("Test Person").length).toBeGreaterThan(0);
    expect(screen.queryByText(/omitted \d/i)).not.toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Reset focus" }));
    expect(screen.getByLabelText("Search within this neighborhood")).toHaveValue("");
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

  it("labels and filters distinct work evidence without exposing its node code", async () => {
    render(
      <OntologyExplorer
        focusNodeType="node_post"
        focusNodeId={POST_ID}
        neighborhood={neighborhood({
          nodes: [
            neighborhood().nodes[0],
            {
              node_id: CONSTRUCT_ID,
              node_type_code: "node_occupational_construct",
              ontology_class_iri: "https://example.test/OccupationalConstruct",
              display_label: "Problem Sensitivity",
              truth_status_code: null,
              valid_from: null,
              valid_to: null,
              recorded_at: null,
              evidence_count: 1,
              shape_code: "rounded-rectangle",
            },
          ],
          edges: [],
          exact_value_rows: [],
        })}
      />,
    );

    expect(screen.getAllByText("Work evidence").length).toBeGreaterThan(0);
    expect(
      screen.getByText(/Select a work-evidence node to review the records that support it/),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "Select node: Work evidence Problem Sensitivity" }),
    ).toHaveClass("ontology-node-occupational-construct");
    expect(document.querySelectorAll(".ontology-node-occupational-construct rect")).toHaveLength(1);
    expect(screen.queryByText("node_occupational_construct")).not.toBeInTheDocument();

    await userEvent.type(
      screen.getByLabelText("Search within this neighborhood"),
      "Demo public post",
    );
    expect(
      screen.queryByText("Select a work-evidence node to review the records that support it."),
    ).not.toBeInTheDocument();
  });

  it("hosts authorized catalog search without a second destination", () => {
    render(
      <OntologyExplorer
        focusNodeType="node_post"
        focusNodeId={POST_ID}
        neighborhood={neighborhood()}
      />,
    );
    expect(screen.getByRole("heading", { name: "Find work evidence" })).toBeVisible();
    expect(
      screen.getByText(
        "Type two or more letters of a catalog label, then open the supporting record.",
      ),
    ).toBeVisible();
    expect(screen.getByRole("button", { name: "Find matching records" })).toBeVisible();
  });
});
