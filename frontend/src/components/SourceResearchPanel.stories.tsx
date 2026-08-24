import type { Meta, StoryObj } from "@storybook/react-vite";
import { expect, waitFor, within } from "storybook/test";
import type { PostSourceResearch } from "../api";
import { SourceResearchPanel } from "./SourceResearchPanel";

/**
 * SourceResearchPanel fetches from `../api`'s module-level `fetch`, not a
 * prop -- there is no dependency-injection seam and this repo has no MSW
 * addon installed. Stubbing `window.fetch` per story (restored in a
 * `loaders` cleanup) is the lightest mock that still exercises the real
 * component code path, rather than passing fixture data as a prop the
 * component doesn't accept.
 */
function stubFetchOnce(status: number, body: unknown) {
  const original = window.fetch;
  window.fetch = (() =>
    Promise.resolve(new Response(JSON.stringify(body), { status }))) as typeof fetch;
  return () => {
    window.fetch = original;
  };
}

const SUPPORTED_RESEARCH: PostSourceResearch = {
  post_id: "post-demo-public",
  research: [
    {
      lead_ordinal: 0,
      lead_type_code: "url",
      query_text: "https://example.com/press/demo-corp-charging-station",
      evidence_text: "The cited article confirms Demo Corp announced the charging-station build.",
      source_content_unit_id: "content-unit-1",
      source_image_region_id: null,
      research_status_code: "supported",
      sharing_actor_name: "Demo Corp Communications",
      rationale_text: "The article's dateline and author match the post's claimed source.",
      retrievals: [
        {
          url: "https://example.com/press/demo-corp-charging-station",
          title: "Demo Corp announces new charging station",
          passage_text: "Demo Corp today announced construction of a new charging station...",
          cited: true,
        },
      ],
    },
    {
      lead_ordinal: 1,
      lead_type_code: "patent",
      query_text: "US-DEMO-000000-A1",
      evidence_text: "No public patent record matches this citation.",
      source_content_unit_id: null,
      source_image_region_id: "image-region-1",
      research_status_code: "not_enough_information",
      sharing_actor_name: null,
      rationale_text: "The patent office search returned no matching public filing.",
      retrievals: [],
    },
  ],
};

const meta = {
  title: "Evidence/SourceResearchPanel",
  component: SourceResearchPanel,
  args: {
    postId: "post-demo-public",
    accessToken: "demo-token",
    canResearch: true,
  },
  parameters: { layout: "padded" },
} satisfies Meta<typeof SourceResearchPanel>;

export default meta;

type Story = StoryObj<typeof meta>;

export const Populated: Story = {
  loaders: [
    async () => {
      const restore = stubFetchOnce(200, SUPPORTED_RESEARCH);
      return { restore };
    },
  ],
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    await waitFor(() =>
      expect(canvas.getByText("Demo Corp announces new charging station")).toBeInTheDocument(),
    );
    await expect(canvas.getByText("Not enough information")).toBeInTheDocument();
  },
};

export const NoPersistedResearchYet: Story = {
  loaders: [
    async () => {
      stubFetchOnce(200, { post_id: "post-demo-public", research: [] });
      return {};
    },
  ],
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    await waitFor(() =>
      expect(canvas.getByText("No persisted source research yet.")).toBeInTheDocument(),
    );
  },
};

export const ReadOnlyNoResearchButton: Story = {
  args: { canResearch: false },
  loaders: [
    async () => {
      stubFetchOnce(200, { post_id: "post-demo-public", research: [] });
      return {};
    },
  ],
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    await waitFor(() =>
      expect(canvas.getByText("No persisted source research yet.")).toBeInTheDocument(),
    );
    expect(canvas.queryByText("Research sources")).not.toBeInTheDocument();
  },
};

export const FetchFailsClosed: Story = {
  loaders: [
    async () => {
      stubFetchOnce(503, { detail: "source-research provider is unavailable" });
      return {};
    },
  ],
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    await waitFor(() => expect(canvas.getByRole("alert")).toBeInTheDocument());
    await expect(canvas.getByText("Retry")).toBeInTheDocument();
  },
};
