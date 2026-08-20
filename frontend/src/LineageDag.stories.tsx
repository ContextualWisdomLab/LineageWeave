import type { Meta, StoryObj } from "@storybook/react-vite";
import { LineageDag } from "./LineageDag";

const nodes = [
  {
    id: "post-a",
    group: "Apollo",
    label: "Initial event",
    occurred_at: "2026-01-01T00:00:00Z",
    is_root: true,
    is_branch_point: false,
  },
  {
    id: "post-b",
    group: "Apollo",
    label: "Follow-up event",
    occurred_at: "2026-01-02T00:00:00Z",
    is_root: false,
    is_branch_point: false,
  },
];

const deterministicEdge = {
  source: "post-a",
  target: "post-b",
  fused_score: 0.685,
  channel_scores: {
    temporal: 0.9,
    secondary_key: 1,
    text: 0.42,
  },
  channel_evidence: [
    {
      signal_code: "secondary_key" as const,
      signal_label: "Secondary key",
      score: 1,
      weight: 0.25,
      contribution: 0.25,
      rank: 1,
    },
    {
      signal_code: "temporal" as const,
      signal_label: "Time proximity",
      score: 0.9,
      weight: 0.25,
      contribution: 0.225,
      rank: 2,
    },
    {
      signal_code: "text" as const,
      signal_label: "Text similarity",
      score: 0.42,
      weight: 0.5,
      contribution: 0.21,
      rank: 3,
    },
  ],
  reconstruction_version: "rankweave-weighted-convex-v1",
  reconstructed_at: "2026-08-20T04:00:00+00:00",
};

const meta = {
  title: "Buyer/Event Lineage/Exact channel evidence",
  component: LineageDag,
  args: {
    currentPostId: "post-b",
    graph: {
      nodes,
      edges: [deterministicEdge],
      truncated: false,
    },
    onSelectPost: () => undefined,
  },
} satisfies Meta<typeof LineageDag>;

export default meta;
type Story = StoryObj<typeof meta>;

/** Deterministic-only run: the UI explicitly says that no LLM participated. */
export const DeterministicEvidence: Story = {};

/** Optional LLM adjudication actually participated and ranks by contribution. */
export const WithLlmEvidence: Story = {
  args: {
    graph: {
      nodes,
      truncated: false,
      edges: [
        {
          source: "post-a",
          target: "post-b",
          fused_score: 0.67,
          channel_scores: {
            temporal: 0.8,
            secondary_key: 1,
            text: 0.4,
            llm: 0.7,
          },
          channel_evidence: [
            {
              signal_code: "llm",
              signal_label: "LLM adjudication",
              score: 0.7,
              weight: 0.4,
              contribution: 0.28,
              rank: 1,
            },
            {
              signal_code: "secondary_key",
              signal_label: "Secondary key",
              score: 1,
              weight: 0.15,
              contribution: 0.15,
              rank: 2,
            },
            {
              signal_code: "temporal",
              signal_label: "Time proximity",
              score: 0.8,
              weight: 0.15,
              contribution: 0.12,
              rank: 3,
            },
            {
              signal_code: "text",
              signal_label: "Text similarity",
              score: 0.4,
              weight: 0.3,
              contribution: 0.12,
              rank: 4,
            },
          ],
          reconstruction_version: "rankweave-weighted-convex-v1",
          reconstructed_at: "2026-08-20T04:05:00+00:00",
        },
      ],
    },
  },
};
