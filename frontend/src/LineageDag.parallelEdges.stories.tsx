import type { Meta, StoryObj } from "@storybook/react-vite";
import { LineageDag } from "./LineageDag";
import type { LineageGraph } from "./api";

const parallelEdgeGraph: LineageGraph = {
  nodes: [
    {
      id: "rec-001",
      group: "A-100",
      label: "Initial site visit",
      occurred_at: "2026-01-01T00:00:00Z",
      is_root: true,
      is_branch_point: false,
    },
    {
      id: "rec-002",
      group: "A-100",
      label: "Pricing follow-up",
      occurred_at: "2026-01-02T00:00:00Z",
      is_root: false,
      is_branch_point: false,
    },
  ],
  edges: [
    {
      source: "rec-001",
      target: "rec-002",
      fused_score: 0.81,
      interval_relation_code: "interval_contains",
      interval_relation_label: "Contains",
      channel_evidence: [
        {
          signal_code: "text",
          signal_label: "Text similarity",
          score: 0.81,
          weight: 1,
          contribution: 0.81,
          rank: 1,
        },
      ],
    },
    {
      source: "rec-001",
      target: "rec-002",
      fused_score: 0.67,
      interval_relation_code: "interval_overlaps",
      interval_relation_label: "Overlaps",
      channel_evidence: [
        {
          signal_code: "temporal",
          signal_label: "Temporal proximity",
          score: 0.67,
          weight: 1,
          contribution: 0.67,
          rank: 1,
        },
      ],
    },
  ],
};

const meta = {
  title: "Lineage/LineageDag Parallel Edges",
  component: LineageDag,
  args: {
    graph: parallelEdgeGraph,
    onSelectPost: () => undefined,
  },
} satisfies Meta<typeof LineageDag>;

export default meta;
type Story = StoryObj<typeof meta>;

export const ParallelRelationships: Story = {};
