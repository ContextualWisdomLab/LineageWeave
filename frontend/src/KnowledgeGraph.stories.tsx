import type { Meta, StoryObj } from "@storybook/react-vite";
import { KnowledgeGraphView } from "./KnowledgeGraph";
import type { KnowledgeGraph } from "./api";

// Regression fixture for the 2026-08-22 black-node bug: "evidence" nodes
// (source-grounded but not yet catalog-linked) must render with visible
// text on a visible background, not solid black. Covers all three visual
// states -- focus (the post itself), catalog (an already-cataloged
// entity), and evidence -- in one graph so a broken token shows immediately.
const mixedStateGraph: KnowledgeGraph = {
  post_id: "post-1",
  nodes: [
    {
      id: "post-1",
      node_type_code: "node_post",
      node_id: "post-1",
      label: "Case Introduction Meeting",
      is_focus: true,
    },
    {
      id: "team-1",
      node_type_code: "node_team",
      node_id: "team-1",
      label: "Case Design Team",
      ontology_label: "Team",
      is_focus: false,
      is_evidence_text_node: false,
    },
    {
      id: "org-observed",
      node_type_code: "node_corporate_entity",
      node_id: "org-observed",
      label: "Case Main Contractor",
      ontology_label: "organization",
      is_focus: false,
      is_evidence_text_node: true,
    },
    {
      id: "project-observed",
      node_type_code: "node_project",
      node_id: "project-observed",
      label: "Case Grid Project",
      ontology_label: "project",
      is_focus: false,
      is_evidence_text_node: true,
    },
  ],
  edges: [
    {
      source: "post-1",
      target: "team-1",
      edge_type_code: "edge_mention",
      ontology_label: "mentioned in post",
      confidence: 0.9,
      evidence_post_ids: ["post-1"],
    },
    {
      source: "org-observed",
      target: "project-observed",
      edge_type_code: "edge_responsible_for",
      ontology_label: "Responsible for",
      confidence: 0.82,
      evidence_text: "Main Contract - Case Main Contractor",
      evidence_post_ids: ["post-1"],
    },
  ],
};

const directedTemporalGraph: KnowledgeGraph = {
  post_id: "synthetic-post",
  nodes: [
    {
      id: "earlier",
      node_type_code: "semantic_temporal_entity",
      node_id: "earlier",
      label: "Synthetic base release",
      ontology_label: "temporal_entity",
      is_focus: false,
      is_evidence_text_node: true,
    },
    {
      id: "later",
      node_type_code: "semantic_temporal_entity",
      node_id: "later",
      label: "Synthetic multi-stage release",
      ontology_label: "temporal_entity",
      is_focus: false,
      is_evidence_text_node: true,
    },
  ],
  edges: [
    {
      source: "earlier",
      target: "later",
      edge_type_code: "time_before",
      ontology_label: "Before",
      confidence: 0.98,
      evidence_text: "The base release came first.",
      evidence_post_ids: ["synthetic-post"],
    },
  ],
};

const meta = {
  title: "Evidence/KnowledgeGraph",
  component: KnowledgeGraphView,
  parameters: { layout: "padded" },
} satisfies Meta<typeof KnowledgeGraphView>;

export default meta;
type Story = StoryObj<typeof meta>;

export const MixedNodeStates: Story = {
  args: {
    graph: mixedStateGraph,
    onSelectPost: () => undefined,
  },
};

export const EmptyState: Story = {
  args: {
    graph: { post_id: "post-1", nodes: [], edges: [] },
    onSelectPost: () => undefined,
  },
};

export const DirectedTemporalRelation: Story = {
  args: {
    graph: directedTemporalGraph,
  },
};

const longLabelGraph: KnowledgeGraph = {
  post_id: "synthetic-post",
  nodes: [
    {
      id: "focus",
      node_type_code: "node_post",
      node_id: "synthetic-post",
      label: "Initial site visit and project scope discussion",
      ontology_label: "Post",
      is_focus: true,
    },
    {
      id: "later",
      node_type_code: "semantic_temporal_entity",
      node_id: "later",
      label: "Pricing renegotiation: revised quote sent",
      ontology_label: "temporal_entity",
      is_focus: false,
      is_evidence_text_node: true,
    },
  ],
  edges: [
    {
      source: "focus",
      target: "later",
      edge_type_code: "time_before",
      ontology_label: "mentioned in reconstructed continuation",
      confidence: 0.91,
      evidence_text: "The site visit came first.",
      evidence_post_ids: ["synthetic-post"],
    },
  ],
};

export const LongLabels: Story = {
  args: {
    graph: longLabelGraph,
    onSelectPost: () => undefined,
  },
};
