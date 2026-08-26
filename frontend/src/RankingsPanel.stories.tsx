import type { Meta, StoryObj } from "@storybook/react-vite";
import { expect, within } from "storybook/test";
import { RankingsPanel } from "./App";

const rankingResponse = {
  port: "rankings",
  status: "accepted",
  status_reason: null,
  rankings: [
    {
      post_id: "synthetic-post-1",
      post_title: "Renewal evidence update",
      fused_rank: 1,
      channel_evidence: [
        { signal_code: "lexical", signal_label: "Title overlap", channel_rank: 1, weight: 0.75, contribution: 0.012295, rank: 1 },
        { signal_code: "temporal", signal_label: "Newest first", channel_rank: 2, weight: 0.25, contribution: 0.004032, rank: 2 },
      ],
    },
  ],
};

const meta = {
  title: "Evidence/Rankings",
  component: RankingsPanel,
  args: { accessToken: "synthetic-token", onSelectPost: () => undefined },
  beforeEach: () => {
    const fetchBeforeStory = globalThis.fetch;
    globalThis.fetch = async () => new Response(JSON.stringify(rankingResponse), {
      status: 200,
      headers: { "Content-Type": "application/json" },
    });
    return () => { globalThis.fetch = fetchBeforeStory; };
  },
} satisfies Meta<typeof RankingsPanel>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Accepted: Story = {
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    await expect(canvas.getByText("Renewal evidence update")).toBeVisible();
    await expect(canvas.getByText("Use these values to compare ordering signals, not as calibrated scores.")).toBeVisible();
    await expect(canvas.getByRole("list", { name: "Ranking evidence for Renewal evidence update" })).toBeVisible();
  },
};

export const NarrowViewport: Story = {
  ...Accepted,
  parameters: { viewport: { defaultViewport: "mobile1" } },
};
