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
        "Compare this information with the latest evidence before relying on it.",
      ),
    ).toBeInTheDocument();
  });

  it("loads the next opaque cursor page from a truncated live neighborhood", async () => {
    const first = payload({
      truncated: true,
      next_cursor: "after:mentions:post-person",
      limitation_code: "neighborhood_truncated",
    });
    const second = payload({
      truncated: false,
      next_cursor: null,
      limitation_code: null,
      nodes: [
        payload().nodes[0],
        { ...payload().nodes[1], node_id: "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbb2", display_label: "Second person" },
      ],
      edges: [
        {
          ...payload().edges[0],
          edge_id: "mentions:post-second-person",
          target_node_id: "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbb2",
        },
      ],
      exact_value_rows: [
        {
          ...payload().exact_value_rows[0],
          edge_id: "mentions:post-second-person",
          target_node_id: "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbb2",
          target_label: "Second person",
        },
      ],
    });
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
        "More related information is available. Load more or open a record.",
      ),
    ).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Load more related information" }));

    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(2));
    expect(String(fetchMock.mock.calls[1][0])).toContain(
      "cursor=after%3Amentions%3Apost-person",
    );
    expect(screen.getAllByText("Test person").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Second person").length).toBeGreaterThan(0);
  });

  it("names the next action when a hard source bound has no cursor", () => {
    const evidenceBearingEdges = payload().edges.map((edge) => ({
      ...edge,
      evidence_references: [POST_ID],
    }));
    render(
      <OntologyExplorer
        focusNodeType="node_post"
        focusNodeId={POST_ID}
        neighborhood={payload({
          truncated: true,
          next_cursor: null,
          limitation_code: "neighborhood_truncated",
          edges: evidenceBearingEdges,
          exact_value_rows: payload().exact_value_rows.map((row) => ({
            ...row,
            evidence_count: "1",
          })),
        })}
      />,
    );

    expect(
      screen.getByText(
        "Open a related record to review the available information.",
      ),
    ).toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: "Load more related information" }),
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

    await userEvent.click(screen.getByRole("button", { name: /Open relation: mentions from/ }));
    expect(
      screen.getByText(
        "No linked record is available. Review the details above.",
      ),
    ).toBeInTheDocument();
    expect(
      screen.queryByText("Hidden evidence was removed. No omitted count is shown."),
    ).not.toBeInTheDocument();
  });

  it("hides live refocus when the neighborhood is a static catalog snapshot", async () => {
    render(
      <OntologyExplorer
        focusNodeType="node_post"
        focusNodeId={POST_ID}
        neighborhood={payload()}
      />,
    );

    await userEvent.click(screen.getByRole("button", { name: "Open related item: Post Demo post" }));
    expect(screen.queryByRole("button", { name: "Explore related information" })).not.toBeInTheDocument();
  });

  it("clears a previously loaded neighborhood when the access token is removed", async () => {
    const { rerender } = render(
      <OntologyExplorer
        accessToken="token"
        focusNodeType="node_post"
        focusNodeId={POST_ID}
        neighborhood={payload()}
      />,
    );

    expect(screen.getAllByText("Demo post").length).toBeGreaterThan(0);
    rerender(
      <OntologyExplorer
        focusNodeType="node_post"
        focusNodeId={POST_ID}
      />,
    );

    await waitFor(() => {
      expect(screen.queryAllByText("Demo post")).toHaveLength(0);
    });
    expect(
      screen.getByText(
        "No related information is available. Open a record or organization next.",
      ),
    ).toBeInTheDocument();
  });

  it("fetches a new neighborhood after focusing a node with a live token", async () => {
    const first = payload();
    const second = payload({
      focus_node_id: PERSON_ID,
      focus_node_type_code: "node_person",
      nodes: [
        {
          node_id: PERSON_ID,
          node_type_code: "node_person",
          ontology_class_iri: "https://example.test/Person",
          display_label: "Focused person",
          truth_status_code: "truth_observed",
          valid_from: null,
          valid_to: null,
          recorded_at: "2026-01-10T12:00:00+00:00",
          evidence_count: 1,
          shape_code: "ellipse",
        },
      ],
      edges: [],
      exact_value_rows: [],
    });
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => second,
    });
    vi.stubGlobal("fetch", fetchMock);
    render(
      <OntologyExplorer
        accessToken="token"
        focusNodeType="node_post"
        focusNodeId={POST_ID}
        neighborhood={first}
      />,
    );

    await userEvent.click(screen.getByRole("button", { name: "Open related item: Person Test person" }));
    await userEvent.click(screen.getByRole("button", { name: "Explore related information" }));
    expect(await screen.findByText("Focused person")).toBeInTheDocument();
    expect(String(fetchMock.mock.calls[0][0])).toContain(`focus_node_id=${PERSON_ID}`);

    await userEvent.click(screen.getByRole("button", { name: "Reset focus" }));
    await waitFor(() => expect(screen.getAllByText("Demo post")).toHaveLength(2));
    expect(fetchMock).toHaveBeenCalledTimes(1);
  });

  it("accumulates the next page without losing the selected evidence", async () => {
    const first = payload({
      truncated: true,
      next_cursor: "src.v2.opaque-token",
      limitation_code: "neighborhood_truncated",
    });
    const second = payload({
      truncated: false,
      next_cursor: null,
      limitation_code: null,
      nodes: [
        {
          node_id: PERSON_ID,
          node_type_code: "node_person",
          ontology_class_iri: "https://example.test/Person",
          display_label: "Paged person",
          truth_status_code: "truth_observed",
          valid_from: null,
          valid_to: null,
          recorded_at: "2026-01-10T12:00:00+00:00",
          evidence_count: 1,
          shape_code: "ellipse",
        },
      ],
      edges: [],
      exact_value_rows: [],
    });
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
    await userEvent.click(await screen.findByRole("button", { name: /Open relation: mentions from/ }));
    expect(screen.getByLabelText("Supporting details")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Load more related information" }));
    expect(await screen.findByText("Paged person")).toBeInTheDocument();
    expect(screen.getAllByText("Demo post").length).toBeGreaterThan(0);
    expect(screen.getByLabelText("Supporting details")).toBeInTheDocument();
    expect(String(fetchMock.mock.calls[1][0])).toContain("cursor=src.v2.opaque-token");
  });
});
