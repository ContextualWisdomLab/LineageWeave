import type { Meta, StoryObj } from "@storybook/react-vite";
import { fn } from "storybook/test";
import { CitationChip } from "./CitationChip";

const meta = {
  title: "Evidence/CitationChip",
  component: CitationChip,
  args: {
    postId: "post-demo-public",
    postTitle: "Demo public post",
    onOpenEvidence: fn(),
  },
} satisfies Meta<typeof CitationChip>;

export default meta;

type Story = StoryObj<typeof meta>;

export const Default: Story = {};

export const LongTitle: Story = {
  args: {
    postTitle: "Demo Corp January cutoff reconstruction notes",
  },
};
