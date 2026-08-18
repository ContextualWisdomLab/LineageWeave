import type { Meta, StoryObj } from "@storybook/react-vite";
import { WeeklyVoc } from "./WeeklyVoc";

const meta = {
  title: "주간 VOC/WeeklyVoc",
  component: WeeklyVoc,
  args: {
    onOpenItem: () => undefined,
  },
} satisfies Meta<typeof WeeklyVoc>;

export default meta;

type Story = StoryObj<typeof meta>;

export const SeededWeek: Story = {
  args: {
    items: [
      {
        post_id: "post-1",
        post_title: "Public post",
        voc_type_code: "voc",
        voc_type_label: "Voice of Customer",
        visibility_code: "public",
        created_at: "2026-01-01T00:00:00Z",
      },
    ],
  },
};

export const EmptyWeek: Story = {
  args: {
    items: [],
  },
};
