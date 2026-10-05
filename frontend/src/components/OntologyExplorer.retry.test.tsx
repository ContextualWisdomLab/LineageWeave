import { afterEach, describe, expect, it, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { OntologyNeighborhoodPayload } from "../api";
import { OntologyExplorer } from "./OntologyExplorer";

const postId = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa1";
const evidence: OntologyNeighborhoodPayload = {
  focus_node_type_code: "node_post", focus_node_id: postId,
  truncated: false, next_cursor: null, limitation_code: null,
  nodes: [{
    node_id: postId, node_type_code: "node_post",
    ontology_class_iri: "https://example.test/Post", display_label: "Demo recovery post",
    truth_status_code: "truth_observed", valid_from: null, valid_to: null,
    recorded_at: "2026-01-10T12:00:00+00:00", evidence_count: 1, shape_code: "rectangle",
  }],
  edges: [], exact_value_rows: [], jsonld: { "@graph": [] },
};

const success = (data: OntologyNeighborhoodPayload) => ({
  ok: true, status: 200, json: async () => data,
});
const failure = (status: number) => ({
  ok: false, status, json: async () => ({ detail: "synthetic-private-diagnostic" }),
});

afterEach(() => vi.unstubAllGlobals());

describe("OntologyExplorer request recovery", () => {
  it("retries an initial failure with the same focus and cutoff and waits for evidence", async () => {
    let resolveRetry!: (response: ReturnType<typeof success>) => void;
    const fetchMock = vi.fn().mockResolvedValueOnce(failure(503))
      .mockImplementationOnce(() => new Promise((resolve) => { resolveRetry = resolve; }));
    vi.stubGlobal("fetch", fetchMock);
    render(<OntologyExplorer accessToken="synthetic-token" focusNodeType="node_post"
      focusNodeId={postId} knowledgeCutoff="2026-01-15T12:00:00Z" />);

    const retry = await screen.findByRole("button", { name: "Retry" });
    expect(screen.getByRole("alert")).toContainElement(retry);
    expect(screen.queryByText("synthetic-private-diagnostic")).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Export CSV" })).toBeDisabled();
    await userEvent.click(retry);
    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(2));
    expect(fetchMock.mock.calls[1]).toEqual(fetchMock.mock.calls[0]);
    expect(screen.queryByRole("button", { name: "Retry" })).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Export JSON-LD" })).toBeDisabled();
    resolveRetry(success(evidence));
    expect(await screen.findByRole("button", { name: "Select node: Post Demo recovery post" })).toBeVisible();
    expect(screen.getByRole("button", { name: "Export JSON-LD" })).toBeEnabled();
  });

  it("retries the failed continuation cursor rather than restarting the first page", async () => {
    const first = { ...evidence, truncated: true, next_cursor: "src.v2.synthetic-cursor" };
    const next = { ...evidence, nodes: [{ ...evidence.nodes[0], node_id: "synthetic-next-post",
      display_label: "Demo continued post" }] };
    const fetchMock = vi.fn().mockResolvedValueOnce(success(first))
      .mockResolvedValueOnce(failure(503)).mockResolvedValueOnce(success(next));
    vi.stubGlobal("fetch", fetchMock);
    render(<OntologyExplorer accessToken="synthetic-token" focusNodeType="node_post" focusNodeId={postId} />);
    await userEvent.click(await screen.findByRole("button", { name: "Load next relation page" }));
    const retry = await screen.findByRole("button", { name: "Retry" });
    expect(screen.getByRole("button", { name: "Select node: Post Demo recovery post" })).toBeVisible();
    expect(screen.queryByRole("button", { name: "Load next relation page" })).not.toBeInTheDocument();
    await userEvent.click(retry);
    expect(await screen.findByRole("button", { name: "Select node: Post Demo continued post" })).toBeVisible();
    expect(fetchMock.mock.calls[2]).toEqual(fetchMock.mock.calls[1]);
    expect(String(fetchMock.mock.calls[2][0])).toContain("cursor=src.v2.synthetic-cursor");
    expect(screen.getByRole("button", { name: "Select node: Post Demo recovery post" })).toBeVisible();
  });

  it.each([403, 404])("does not offer request retry for denied evidence (%s)", async (status) => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(failure(status)));
    render(<OntologyExplorer accessToken="synthetic-token" focusNodeType="node_post" focusNodeId={postId} />);
    await screen.findByText("Related information is unavailable for this record. Open a visible post next.");
    expect(screen.queryByRole("button", { name: "Retry" })).not.toBeInTheDocument();
  });

  it.each([403, 404])("does not offer pagination after continuation is denied (%s)", async (status) => {
    const first = { ...evidence, truncated: true, next_cursor: "src.v2.synthetic-cursor" };
    const fetchMock = vi.fn().mockResolvedValueOnce(success(first))
      .mockResolvedValueOnce(failure(status));
    vi.stubGlobal("fetch", fetchMock);
    render(<OntologyExplorer accessToken="synthetic-token" focusNodeType="node_post" focusNodeId={postId} />);
    await userEvent.click(await screen.findByRole("button", { name: "Load next relation page" }));
    await screen.findByText("Related information is unavailable for this record. Open a visible post next.");
    expect(screen.queryByRole("button", { name: "Load next relation page" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Retry" })).not.toBeInTheDocument();
    expect(fetchMock).toHaveBeenCalledTimes(2);
  });
});
