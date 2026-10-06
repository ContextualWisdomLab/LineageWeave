import type { Meta, StoryObj } from "@storybook/react-vite";
import { expect, userEvent, within } from "storybook/test";
import type { OntologyNeighborhoodPayload } from "../api";
import { OntologyExplorer } from "./OntologyExplorer";

const meta = {
  title: "Evidence/OntologyExplorerRetry",
  component: OntologyExplorer,
  args: {
    accessToken: "synthetic-story-token",
    focusNodeType: "node_post",
    focusNodeId: "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa1",
  },
  beforeEach: () => {
    const originalFetch = globalThis.fetch;
    globalThis.fetch = (input, init) => {
      const url = input instanceof Request ? input.url : String(input);
      if (new URL(url, window.location.href).pathname === "/api/ontology/neighborhood") {
        return Promise.resolve(new Response(
          JSON.stringify({ detail: "synthetic-private-diagnostic" }),
          { status: 503, headers: { "Content-Type": "application/json" } },
        ));
      }
      return originalFetch(input, init);
    };
    return () => { globalThis.fetch = originalFetch; };
  },
} satisfies Meta<typeof OntologyExplorer>;

export default meta;
type Story = StoryObj<typeof meta>;

export const InitialRequestRetry: Story = {
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    const retry = await canvas.findByRole("button", { name: "Retry" });
    await expect(canvas.getByRole("alert")).toContainElement(retry);
    await expect(canvas.getByRole("button", { name: "Export CSV" })).toBeDisabled();
    await expect(canvas.queryByText("synthetic-private-diagnostic")).not.toBeInTheDocument();
  },
};

export const DeniedRefocusReset: Story = {
  args: {
    neighborhood: {
      focus_node_type_code: "node_post",
      focus_node_id: "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa1",
      truncated: false, next_cursor: null, limitation_code: null,
      nodes: [{
        node_id: "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa1", node_type_code: "node_post",
        ontology_class_iri: "https://example.test/Post", display_label: "Demo recovery post",
        truth_status_code: "truth_observed", valid_from: null, valid_to: null,
        recorded_at: "2026-01-10T12:00:00+00:00", evidence_count: 1, shape_code: "rectangle",
      }],
      edges: [], exact_value_rows: [], jsonld: { "@graph": [] },
    } satisfies OntologyNeighborhoodPayload,
  },
  beforeEach: () => {
    const originalFetch = globalThis.fetch;
    let reads = 0;
    globalThis.fetch = (input, init) => {
      const url = input instanceof Request ? input.url : String(input);
      if (new URL(url, window.location.href).pathname === "/api/ontology/neighborhood") {
        reads += 1;
        return Promise.resolve(new Response(JSON.stringify({ detail: "synthetic-private-diagnostic" }),
          { status: reads === 1 ? 403 : 503, headers: { "Content-Type": "application/json" } }));
      }
      return originalFetch(input, init);
    };
    return () => { globalThis.fetch = originalFetch; };
  },
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    await userEvent.click(canvas.getByRole("button", { name: "Select node: Post Demo recovery post" }));
    await userEvent.click(canvas.getByRole("button", { name: "Focus this node next" }));
    await canvas.findByText("Related information is unavailable for this record. Open a visible post next.");
    await expect(canvas.queryByRole("button", { name: "Retry" })).not.toBeInTheDocument();
    await userEvent.click(canvas.getByRole("button", { name: "Reset focus" }));
    await expect(await canvas.findByRole("button", { name: "Retry" })).toBeVisible();
    await expect(canvas.getByRole("button", { name: "Export CSV" })).toBeDisabled();
    await expect(canvas.getByRole("button", { name: "Export JSON-LD" })).toBeDisabled();
    await expect(canvas.queryByText("Demo recovery post")).not.toBeInTheDocument();
    await expect(canvas.queryByText("synthetic-private-diagnostic")).not.toBeInTheDocument();
  },
};
