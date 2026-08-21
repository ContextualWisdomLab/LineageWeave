import type { Meta, StoryObj } from "@storybook/react-vite";
import type { LineageGraph } from "../api";
import { LineageDag } from "../LineageDag";

const branchingGraph: LineageGraph = {
  nodes: [
    {
      id: "record-001",
      group: "DEMO-PROJECT",
      label: "Initial scope discussion",
      occurred_at: "2026-01-01T09:00:00Z",
      is_root: true,
      is_branch_point: false,
    },
    {
      id: "record-002",
      group: "DEMO-PROJECT",
      label: "Commercial terms follow-up",
      occurred_at: "2026-01-05T09:00:00Z",
      is_root: false,
      is_branch_point: true,
    },
    {
      id: "record-003",
      group: "DEMO-PROJECT",
      label: "Revised quotation issued",
      occurred_at: "2026-01-09T09:00:00Z",
      is_root: false,
      is_branch_point: false,
    },
    {
      id: "record-004",
      group: "DEMO-PROJECT",
      label: "Delivery schedule question",
      occurred_at: "2026-01-06T09:00:00Z",
      is_root: false,
      is_branch_point: false,
    },
    {
      id: "record-005",
      group: "DEMO-PROJECT",
      label: "Delivery schedule confirmed",
      occurred_at: "2026-01-11T09:00:00Z",
      is_root: false,
      is_branch_point: false,
    },
  ],
  edges: [
    { source: "record-001", target: "record-002", fused_score: 0.83 },
    { source: "record-002", target: "record-003", fused_score: 0.94 },
    { source: "record-002", target: "record-004", fused_score: 0.87 },
    { source: "record-004", target: "record-005", fused_score: 0.9 },
  ],
};

const meta = {
  title: "Analysis/LineageDag",
  component: LineageDag,
  parameters: {
    layout: "padded",
  },
  args: {
    graph: branchingGraph,
    currentPostId: "record-004",
    onSelectPost: () => undefined,
  },
} satisfies Meta<typeof LineageDag>;

export default meta;

type Story = StoryObj<typeof meta>;

export const BranchingEvidence: Story = {};

export const RootSelected: Story = {
  args: {
    currentPostId: "record-001",
  },
};

export const Empty: Story = {
  args: {
    graph: { nodes: [], edges: [] },
    currentPostId: undefined,
  },
};
