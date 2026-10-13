import type { Meta, StoryObj } from "@storybook/react-vite";
import { expect, within } from "storybook/test";
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
