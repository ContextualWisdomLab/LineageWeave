import type { Meta, StoryObj } from "@storybook/react-vite";
import { LineageDag } from "./LineageDag";

const meta = {
  title: "Buyer/Event Lineage/Exact channel evidence",
  component: LineageDag,
  args: {
    currentPostId: "post-b",
    graph: {
      nodes: [
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
      ],
      edges: [
        {
          source: "post-a",
          target: "post-b",
          fused_score: 0.78,
          channel_scores: {
            temporal: 0.9,
            secondary_key: 1,
            text: 0.42,
          },
        },
      ],
      truncated: false,
    },
    onSelectPost: () => undefined,
  },
} satisfies Meta<typeof LineageDag>;

export default meta;
type Story = StoryObj<typeof meta>;

/** A selected edge with deterministic channels and an unavailable LLM channel. */
export const DeterministicEvidence: Story = {};

/** A selected edge whose optional LLM adjudication was actually available. */
export const WithLlmEvidence: Story = {
  args: {
    graph: {
      ...meta.args.graph,
      edges: [
        {
          ...meta.args.graph.edges[0],
          channel_scores: {
            ...meta.args.graph.edges[0].channel_scores,
            llm: 0.71,
          },
        },
      ],
    },
  },
};
