import type { Meta, StoryObj } from "@storybook/react-vite";
import { expect, within } from "storybook/test";

import { HistoricalRelatedPanel } from "../App";
import "../App.css";

const meta = {
  title: "Post/Historical related information",
  component: HistoricalRelatedPanel,
  args: {
    postId: "synthetic-post",
    accessToken: "synthetic-token",
    knowledgeCutoff: "2026-01-12T12:00:00Z",
  },
} satisfies Meta<typeof HistoricalRelatedPanel>;

export default meta;
type Story = StoryObj<typeof meta>;

export const CutoffEvidence: Story = {
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    await expect(canvas.getByText("Only relationships supported by this date appear here. Open a post to inspect its available history.")).toBeVisible();
    await expect(canvas.getByRole("button", { name: "View related information" })).toHaveAttribute("aria-expanded", "false");
  },
};

export const NarrowViewport: Story = {
  parameters: { viewport: { defaultViewport: "mobile1" } },
};
