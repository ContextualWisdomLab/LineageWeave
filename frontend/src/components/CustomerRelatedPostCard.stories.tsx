import type { Meta, StoryObj } from "@storybook/react-vite";
import { CustomerRelatedPostCard } from "./CustomerEntityTree";
import "../App.css";

const meta = {
  title: "CustomerMaster/CustomerRelatedPostCard",
  component: CustomerRelatedPostCard,
  args: {
    postId: "post-1",
    postTitle: "2026년 1분기 공급망 현황 보고",
    postBodyExcerpt: "이번 분기 반도체 공급망 안정화를 위한 협력 방안을 논의했습니다.",
    postBodyTruncated: false,
    onOpenPost: () => undefined,
  },
} satisfies Meta<typeof CustomerRelatedPostCard>;

export default meta;

type Story = StoryObj<typeof meta>;

export const Default: Story = {};

export const Truncated: Story = {
  args: { postBodyTruncated: true },
};

export const NoBody: Story = {
  args: { postBodyExcerpt: null },
};
