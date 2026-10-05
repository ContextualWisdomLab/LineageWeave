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
  beforeEach: ({ parameters }) => {
    const originalFetch = globalThis.fetch;
    globalThis.fetch = (input, init) => {
      const url = input instanceof Request ? input.url : String(input);
      const requestUrl = new URL(url, window.location.href);
      if (requestUrl.pathname === "/api/ontology/neighborhood") {
        if (parameters.deniedContinuation && !requestUrl.searchParams.has("cursor")) {
          const first: OntologyNeighborhoodPayload = {
            focus_node_type_code: "node_post",
            focus_node_id: "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa1",
            truncated: true, next_cursor: "src.v2.synthetic-cursor", limitation_code: null,
            nodes: [], edges: [], exact_value_rows: [], jsonld: { "@graph": [] },
          };
          return Promise.resolve(new Response(JSON.stringify(first), {
            status: 200, headers: { "Content-Type": "application/json" },
          }));
        }
        return Promise.resolve(new Response(
          JSON.stringify({ detail: "synthetic-private-diagnostic" }),
          { status: parameters.deniedContinuation ? 403 : 503, headers: { "Content-Type": "application/json" } },
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

export const DeniedContinuation: Story = {
  parameters: { deniedContinuation: true },
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    await userEvent.click(await canvas.findByRole("button", { name: "Load next relation page" }));
    await canvas.findByText("Related information is unavailable for this record. Open a visible post next.");
    await expect(canvas.queryByRole("button", { name: "Load next relation page" })).not.toBeInTheDocument();
    await expect(canvas.queryByRole("button", { name: "Retry" })).not.toBeInTheDocument();
  },
};
