import type { Meta, StoryObj } from "@storybook/react-vite";
import { expect, userEvent, within } from "storybook/test";
import { PostList } from "../App";

const response = (value: unknown) => new Response(JSON.stringify(value), {
  headers: { "Content-Type": "application/json" },
});

const meta = {
  title: "Workspace/Post board",
  component: PostList,
  args: { accessToken: "synthetic-token" },
  parameters: { layout: "fullscreen" },
  decorators: [(Story) => <div className="app-shell"><main><Story /></main></div>],
  beforeEach: () => {
    const previousFetch = globalThis.fetch;
    globalThis.fetch = async (input) => {
      const url = new URL(String(input), window.location.origin);
      if (url.pathname === "/api/me") return response({ permission_codes: [], corporate_entities: [] });
      if (url.pathname === "/api/posts" && url.searchParams.has("search")) {
        return new Promise<Response>(() => undefined);
      }
      if (url.pathname === "/api/posts") return response({
        posts: [{
          post_id: "synthetic-post",
          post_title: "Synthetic source record",
          post_body_excerpt: "A synthetic record awaiting a new search.",
          created_at: "2026-01-01T00:00:00Z",
          voc_type_code: "voc",
          voc_type_label: "Voice of Customer",
          visibility_code: "public",
          visibility_label: "Public",
        }],
        total_count: 1,
        limit: 50,
        offset: 0,
      });
      return response({});
    };
    return () => { globalThis.fetch = previousFetch; };
  },
} satisfies Meta<typeof PostList>;

export default meta;
type Story = StoryObj<typeof meta>;

export const SearchPending: Story = {
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    await canvas.findByRole("button", { name: "View post: Synthetic source record" });
    await userEvent.type(canvas.getByRole("searchbox", { name: "Search semantic evidence" }), "different evidence");
    await userEvent.click(canvas.getByRole("button", { name: "Search" }));
    await expect(canvas.getByRole("status")).toHaveTextContent("Loading posts...");
    await expect(canvas.queryByRole("button", { name: "View post: Synthetic source record" })).not.toBeInTheDocument();
  },
};

export const NarrowViewport: Story = {
  ...SearchPending,
  parameters: { viewport: { defaultViewport: "mobile1" } },
};
