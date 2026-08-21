import type { Meta, StoryObj } from "@storybook/react";

import { AskProjectHistoryLinks } from "./AskProjectHistoryLinks";

const meta = {
  title: "Buyer/Ask Project History Links",
  component: AskProjectHistoryLinks,
  args: {
    accessToken: "storybook-token",
    links: [
      {
        project_key: "P-100",
        project_name: "Synthetic renewal",
        focus_post_id: "post-voc",
        source_post_ids: ["post-spec", "post-voc"],
        knowledge_cutoff: "2026-08-20T12:00:00Z",
        truth_status_code: "observed",
      },
    ],
    truncated: false,
    onOpenPost: () => undefined,
  },
} satisfies Meta<typeof AskProjectHistoryLinks>;

export default meta;
type Story = StoryObj<typeof meta>;

export const ObservedProject: Story = {};

export const InferredAndTruncated: Story = {
  args: {
    links: [
      {
        project_key: "semantic-project",
        project_name: "Semantic project candidate",
        focus_post_id: "post-candidate",
        source_post_ids: ["post-candidate"],
        knowledge_cutoff: "2026-08-20T12:00:00Z",
        truth_status_code: "inferred",
      },
    ],
    truncated: true,
  },
};
