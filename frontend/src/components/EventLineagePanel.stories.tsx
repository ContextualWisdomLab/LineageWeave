import type { Meta, StoryObj } from "@storybook/react-vite";
import { EventLineagePanel } from "./EventLineagePanel";

const meta = {
  title: "게시판/EventLineagePanel",
  component: EventLineagePanel,
  args: {
    postId: "post-1",
    onSelectNode: () => undefined,
    lineage: {
      post_id: "post-1",
      direct: [],
      indirect: [{ post_id: "post-2", post_title: "Linked post" }],
    },
    graph: {
      nodes: [
        {
          id: "post-1",
          group: "A-100",
          label: "Public post",
          occurred_at: "2026-01-01T00:00:00Z",
          is_root: true,
          is_branch_point: false,
        },
        {
          id: "post-2",
          group: "A-100",
          label: "Linked post",
          occurred_at: "2026-01-02T00:00:00Z",
          is_root: false,
          is_branch_point: false,
        },
      ],
      edges: [{ source: "post-1", target: "post-2", fused_score: 0.8 }],
    },
  },
} satisfies Meta<typeof EventLineagePanel>;

export default meta;

type Story = StoryObj<typeof meta>;

export const SeededDag: Story = {};

export const Empty: Story = {
  args: {
    lineage: { post_id: "post-1", direct: [], indirect: [] },
    graph: { nodes: [], edges: [] },
  },
};
