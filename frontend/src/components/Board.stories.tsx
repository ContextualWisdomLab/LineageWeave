import type { Meta, StoryObj } from "@storybook/react-vite";
import { Board } from "./Board";

const meta = {
  title: "게시판/Board",
  component: Board,
  args: {
    onOpenItem: () => undefined,
    onSearch: async () => [],
  },
} satisfies Meta<typeof Board>;

export default meta;

type Story = StoryObj<typeof meta>;

export const SeededBoard: Story = {
  args: {
    items: [
      {
        post_id: "post-news",
        post_title: "주간 신문 2026-W02",
        voc_type_code: "voc",
        visibility_code: "public",
        created_at: "2026-01-13T10:00:00Z",
        thread_group_key: "newspaper-week",
        edition: {
          kind: "week",
          period_code: "2026-W02",
          sections: [
            {
              grain_code: "corporate",
              unit_id: "corp-1",
              unit_label: "Demo Corp",
              titles: ["Public post"],
              empty_next_action: null,
            },
          ],
          empty_next_action: null,
        },
      },
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

export const EmptyBoard: Story = {
  args: {
    items: [],
  },
};
