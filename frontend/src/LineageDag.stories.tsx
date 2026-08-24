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
    { source: "record-root", target: "record-a", fused_score: 0.91, channel_scores: {} },
    { source: "record-root", target: "record-b", fused_score: 0.78, channel_scores: {} },
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

const longLabelMultiTopic: LineageGraph = {
  nodes: [
    {
      id: "rec-001",
      group: "A-100",
      label: "Initial site visit and project scope discussion",
      occurred_at: "2026-01-01T00:00:00Z",
      is_root: true,
      is_branch_point: false,
    },
    {
      id: "rec-002",
      group: "A-100",
      label: "Pricing renegotiation follow-up",
      occurred_at: "2026-01-06T00:00:00Z",
      is_root: false,
      is_branch_point: true,
    },
    {
      id: "rec-003",
      group: "A-100",
      label: "Pricing renegotiation: revised quote sent",
      occurred_at: "2026-01-10T00:00:00Z",
      is_root: false,
      is_branch_point: false,
    },
    {
      id: "rec-004",
      group: "A-100",
      label: "Delivery schedule question raised",
      occurred_at: "2026-01-07T00:00:00Z",
      is_root: false,
      is_branch_point: false,
    },
    {
      id: "rec-101",
      group: "B-200",
      label: "Technical specification review meeting",
      occurred_at: "2026-01-03T00:00:00Z",
      is_root: true,
      is_branch_point: false,
    },
  ],
  edges: [
    { source: "rec-001", target: "rec-002", fused_score: 0.8, channel_scores: {} },
    { source: "rec-002", target: "rec-003", fused_score: 0.9, channel_scores: {} },
    { source: "rec-002", target: "rec-004", fused_score: 0.85, channel_scores: {} },
  ],
};

export const LongLabelMultiTopic: Story = {
  args: {
    graph: longLabelMultiTopic,
    currentPostId: "rec-002",
    onSelectPost: () => undefined,
  },
};
