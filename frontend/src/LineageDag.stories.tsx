import type { Meta, StoryObj } from "@storybook/react-vite";
import { LineageDag } from "./LineageDag";
import type { LineageGraph } from "./api";

const a100Graph: LineageGraph = {
  nodes: [
    {
      id: "rec-001",
      group: "A-100",
      label: "Initial site visit and project scope discussion",
      occurred_at: "2026-01-01T00:00:00",
      is_root: true,
      is_branch_point: false,
    },
    {
      id: "rec-002",
      group: "A-100",
      label: "Pricing renegotiation follow-up",
      occurred_at: "2026-01-06T00:00:00",
      is_root: false,
      is_branch_point: true,
    },
    {
      id: "rec-003",
      group: "A-100",
      label: "Pricing renegotiation: revised quote sent",
      occurred_at: "2026-01-10T00:00:00",
      is_root: false,
      is_branch_point: false,
    },
    {
      id: "rec-004",
      group: "A-100",
      label: "Delivery schedule question raised",
      occurred_at: "2026-01-07T00:00:00",
      is_root: false,
      is_branch_point: false,
    },
  ],
  edges: [
    {
      source: "rec-001",
      target: "rec-002",
      fused_score: 0.8,
      interval_relation_code: "interval_before",
      interval_relation_label: "Before",
    },
    {
      source: "rec-002",
      target: "rec-003",
      fused_score: 0.9,
      interval_relation_code: "interval_contains",
      interval_relation_label: "Contains",
    },
    {
      source: "rec-002",
      target: "rec-004",
      fused_score: 0.85,
      interval_relation_code: "interval_overlaps",
      interval_relation_label: "Overlaps",
    },
  ],
};

const meta = {
  title: "Lineage/LineageDag",
  component: LineageDag,
  args: {
    graph: a100Graph,
    onSelectPost: () => undefined,
    currentPostId: "rec-002",
  },
} satisfies Meta<typeof LineageDag>;

export default meta;

type Story = StoryObj<typeof meta>;

export const ContainsAndOverlaps: Story = {};

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
    currentPostId: undefined,
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
    currentPostId: undefined,
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
    currentPostId: undefined,
  },
};
