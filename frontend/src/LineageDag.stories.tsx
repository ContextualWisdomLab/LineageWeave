import type { Meta, StoryObj } from "@storybook/react-vite";
import { LineageDag } from "./LineageDag";
import type { LineageGraph } from "./api";

const meta = {
  title: "Lineage/LineageDag",
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

// Edge case: no reconstructed lineage yet -- must not render an empty SVG.
export const Empty: Story = {
  args: {
    graph: { nodes: [], edges: [] },
  },
};

export const SingleBranch: Story = {
  args: {
    graph: {
      nodes: [
        { id: "a1", group: "Northwind Renewal", label: "Kickoff note", occurred_at: "2026-01-01T00:00:00Z", is_root: true, is_branch_point: false },
        { id: "a2", group: "Northwind Renewal", label: "Follow-up call", occurred_at: "2026-01-04T00:00:00Z", is_root: false, is_branch_point: false },
        { id: "a3", group: "Northwind Renewal", label: "Contract signed", occurred_at: "2026-01-10T00:00:00Z", is_root: false, is_branch_point: false },
      ],
      edges: [
        { source: "a1", target: "a2", fused_score: 0.86 },
        { source: "a2", target: "a3", fused_score: 0.91 },
      ],
    } satisfies LineageGraph,
  },
};

// The multi-branch, git-branch-style case the Ask Agent answer view relies on:
// several independent lineage threads rendered as separate figures, plus one
// thread with an actual fork (a branch point with two children).
export const MultipleGitStyleBranches: Story = {
  args: {
    graph: {
      nodes: [
        { id: "a1", group: "Northwind Renewal", label: "Kickoff note", occurred_at: "2026-01-01T00:00:00Z", is_root: true, is_branch_point: true },
        { id: "a2", group: "Northwind Renewal", label: "Legal review", occurred_at: "2026-01-04T00:00:00Z", is_root: false, is_branch_point: false },
        { id: "a3", group: "Northwind Renewal", label: "Pricing review", occurred_at: "2026-01-04T00:00:00Z", is_root: false, is_branch_point: false },
        { id: "b1", group: "Acme Onboarding", label: "Welcome call", occurred_at: "2026-02-01T00:00:00Z", is_root: true, is_branch_point: false },
        { id: "b2", group: "Acme Onboarding", label: "Access provisioned", occurred_at: "2026-02-03T00:00:00Z", is_root: false, is_branch_point: false },
      ],
      edges: [
        { source: "a1", target: "a2", fused_score: 0.78 },
        { source: "a1", target: "a3", fused_score: 0.64 },
        { source: "b1", target: "b2", fused_score: 0.9 },
      ],
    } satisfies LineageGraph,
    currentPostId: "a1",
  },
};

// Edge case: a node with no explicit group (or a raw UUID group id from a
// partially-processed corpus) must still render, bucketed under "Ungrouped".
export const UngroupedNode: Story = {
  args: {
    graph: {
      nodes: [{ id: "u1", group: "", label: "Standalone note with no thread yet", occurred_at: "2026-01-01T00:00:00Z", is_root: true, is_branch_point: false }],
      edges: [],
    } satisfies LineageGraph,
  },
};

// Edge case: a very long post title must truncate in the graph without
// breaking layout, while the full title stays available to screen readers.
export const LongNodeLabel: Story = {
  args: {
    graph: {
      nodes: [
        {
          id: "a1",
          group: "Northwind Renewal",
          label: "Quarterly vendor renewal kickoff call with legal, procurement, and finance stakeholders",
          occurred_at: "2026-01-01T00:00:00Z",
          is_root: true,
          is_branch_point: false,
        },
      ],
      edges: [],
    } satisfies LineageGraph,
  },
};
