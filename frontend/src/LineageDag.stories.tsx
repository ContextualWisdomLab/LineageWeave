import type { Meta, StoryObj } from "@storybook/react-vite";
import { LineageDag } from "./LineageDag";

const meta = {
  title: "Evidence/LineageDag",
  component: LineageDag,
  args: {
    onSelectPost: () => undefined,
    graph: {
      nodes: [
        {
          id: "rec-002",
          group: "A-100",
          label: "Kickoff recap",
          occurred_at: "2026-01-02T00:00:00",
          is_root: true,
          is_branch_point: true,
        },
        {
          id: "rec-003",
          group: "A-100",
          label: "Pricing follow-up",
          occurred_at: "2026-01-03T00:00:00",
          is_root: false,
          is_branch_point: false,
        },
      ],
      edges: [
        {
          source: "rec-002",
          target: "rec-003",
          fused_score: 0.7,
          channel_evidence: [
            {
              signal_code: "text",
              signal_label: "Text similarity",
              score: 0.5,
              weight: 0.5,
              contribution: 0.25,
              rank: 1,
            },
            {
              signal_code: "temporal",
              signal_label: "Temporal proximity",
              score: 0.8,
              weight: 0.25,
              contribution: 0.2,
              rank: 2,
            },
          ],
        },
      ],
      reconstruction: {
        reconstruction_version: "lineageweave.reconstruct/2.14.0",
        generated_at: "2026-08-21T12:00:00+00:00",
        min_fused_score: 0.3,
        candidate_window: 50,
        active_weights: [
          { signal_code: "temporal", signal_weight: 0.25 },
          { signal_code: "text", signal_weight: 0.5 },
        ],
      },
    },
  },
} satisfies Meta<typeof LineageDag>;

export default meta;

type Story = StoryObj<typeof meta>;

export const ConnectionEvidence: Story = {};

export const NoLlmChannel: Story = {};
