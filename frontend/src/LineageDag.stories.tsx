import type { Meta, StoryObj } from "@storybook/react-vite";
import { expect, within } from "storybook/test";
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
      fused_score: 0.797623792218737,
      interval_relation_code: "interval_contains",
      interval_relation_label: "Contains",
      channel_evidence: [
        { signal_code: "temporal", signal_label: "Temporal proximity", score: 0.8, weight: 0.5306114573429468, contribution: 0.4244891658743575, rank: 1 },
        { signal_code: "secondary_key", signal_label: "Secondary key", score: 1, weight: 0.27688071002092646, contribution: 0.27688071002092646, rank: 2 },
        { signal_code: "text", signal_label: "Text similarity", score: 0.5, weight: 0.1925078326361269, contribution: 0.09625391631806345, rank: 3 },
      ],
    },
    {
      source: "rec-002",
      target: "rec-004",
      fused_score: 0.85,
      interval_relation_code: "interval_overlaps",
      interval_relation_label: "Overlaps",
    },
  ],
  reconstruction: {
    reconstruction_version: "lineageweave.reconstruct/2.14.0",
    generated_at: "2026-08-21T12:00:00+00:00",
    min_fused_score: 0.3,
    candidate_window: 50,
    active_weights: [
      // fast-mlsirm estimate_fixture_channel_weights(), not hand-picked UI weights.
      { signal_code: "secondary_key", signal_weight: 0.27688071002092646 },
      { signal_code: "temporal", signal_weight: 0.5306114573429468 },
      { signal_code: "text", signal_weight: 0.1925078326361269 },
    ],
  },
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

export const ConnectionEvidence: Story = {};

export const NoLlmChannel: Story = {};
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

// Mirrors the live Figma mobile authority: a 322px viewport contains an
// intrinsically wider lineage canvas and gives the buyer explicit scroll help.
export const MobileScrollable: Story = {
  decorators: [
    (Story) => (
      <div style={{ width: 322 }}>
        <Story />
      </div>
    ),
  ],
  args: {
    graph: {
      nodes: [
        { id: "m1", group: "DEMO-PROJECT", label: "Initial scope", occurred_at: "2026-01-01T00:00:00Z", is_root: true, is_branch_point: false },
        { id: "m2", group: "DEMO-PROJECT", label: "Terms follow-up", occurred_at: "2026-01-05T00:00:00Z", is_root: false, is_branch_point: true },
        { id: "m3", group: "DEMO-PROJECT", label: "Revised quotation", occurred_at: "2026-01-09T00:00:00Z", is_root: false, is_branch_point: false },
        { id: "m4", group: "DEMO-PROJECT", label: "Delivery question", occurred_at: "2026-01-06T00:00:00Z", is_root: false, is_branch_point: false },
        { id: "m5", group: "DEMO-PROJECT", label: "Delivery confirmed", occurred_at: "2026-01-11T00:00:00Z", is_root: false, is_branch_point: false },
      ],
      edges: [
        { source: "m1", target: "m2", fused_score: 0.83 },
        { source: "m2", target: "m3", fused_score: 0.94 },
        { source: "m2", target: "m4", fused_score: 0.87 },
        { source: "m4", target: "m5", fused_score: 0.9 },
      ],
    } satisfies LineageGraph,
    currentPostId: "m5",
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

// Regression for raw-identity preservation: a named thread whose literal name
// is "Ungrouped" must not absorb records that truly have no reconstruct group.
export const NamedAndTrulyUngrouped: Story = {
  args: {
    graph: {
      nodes: [
        { id: "a1", group: "Alpha", label: "Alpha record", occurred_at: "2026-01-01T00:00:00Z", is_root: true, is_branch_point: false },
        { id: "named-u1", group: "Ungrouped", label: "Named Ungrouped record", occurred_at: "2026-01-02T00:00:00Z", is_root: true, is_branch_point: false },
        { id: "loose-u1", group: "", label: "Truly ungrouped record", occurred_at: "2026-01-03T00:00:00Z", is_root: true, is_branch_point: false },
      ],
      edges: [],
    } satisfies LineageGraph,
    currentPostId: undefined,
  },
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    expect(canvas.getByRole("button", { name: "Open post: Named Ungrouped record" })).toBeVisible();
    expect(canvas.getByRole("button", { name: "Open post: Truly ungrouped record" })).toBeVisible();
    expect(canvas.getAllByRole("region", { name: "Ungrouped lineage viewport" })).toHaveLength(2);

    const figures = [...canvasElement.querySelectorAll(".lineage-dag-group")];
    expect(figures).toHaveLength(3);
    expect(figures[0]).toHaveTextContent("Alpha record");
    expect(figures[1]).toHaveTextContent("Named Ungrouped record");
    expect(figures[1]).not.toHaveTextContent("Truly ungrouped record");
    expect(figures[2]).toHaveTextContent("Truly ungrouped record");
    expect(figures[2]).not.toHaveTextContent("Named Ungrouped record");
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
