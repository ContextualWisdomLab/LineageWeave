import type { Meta, StoryObj } from "@storybook/react-vite";
import { PostBadge } from "./PostBadge";

const meta = {
  title: "AnalysisRun/PostBadge",
  component: PostBadge,
  args: {
    children: "Updated after cutoff",
  },
} satisfies Meta<typeof PostBadge>;

export default meta;

type Story = StoryObj<typeof meta>;

export const UpdatedAfterCutoff: Story = {};

export const InCutoff: Story = {
  args: {
    children: "3 documents",
  },
};
