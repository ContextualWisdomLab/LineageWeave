import type { Meta, StoryObj } from "@storybook/react-vite";
import { LineageDag } from "./LineageDag";
import type { LineageGraph } from "./api";

const branchingGraph: LineageGraph = {
  nodes: [
    {
      id: "record-root",
      group: "DEMO-PROJECT",
      label: "Root record",
      occurred_at: "2026-01-01T00:00:00Z",
      is_root: true,
      is_branch_point: true,
    },
    {
      id: "record-a",
      group: "DEMO-PROJECT",
      label: "Design review",
      occurred_at: "2026-01-02T00:00:00Z",
      is_root: false,
      is_branch_point: false,
    },
    {
      id: "record-b",
      group: "DEMO-PROJECT",
      label: "Commercial follow-up",
      occurred_at: "2026-01-03T00:00:00Z",
      is_root: false,
      is_branch_point: false,
    },
  ],
  edges: [
    { source: "record-root", target: "record-a", fused_score: 0.91 },
    { source: "record-root", target: "record-b", fused_score: 0.78 },
  ],
};

const meta = {
  title: "Evidence/LineageDag",
  component: LineageDag,
  parameters: { layout: "padded" },
} satisfies Meta<typeof LineageDag>;

export default meta;
type Story = StoryObj<typeof meta>;

export const BranchingEventLineage: Story = {
  args: {
    graph: branchingGraph,
    currentPostId: "record-a",
    onSelectPost: () => undefined,
  },
};

export const EmptyState: Story = {
  args: {
    graph: { nodes: [], edges: [] },
    onSelectPost: () => undefined,
  },
};
