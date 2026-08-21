import type { Meta, StoryObj } from "@storybook/react-vite";
import { KnowledgeGraphView } from "./KnowledgeGraph";
import type { KnowledgeGraph } from "./api";

const mixedStateGraph: KnowledgeGraph = {
  post_id: "post-1",
  nodes: [
    {
      id: "post-1",
      node_type_code: "node_post",
      node_id: "post-1",
      label: "Case introduction meeting",
      is_focus: true,
    },
    {
      id: "team-1",
      node_type_code: "node_team",
      node_id: "team-1",
      label: "Case design team",
      ontology_label: "Team",
      is_focus: false,
      is_evidence_text_node: false,
    },
    {
      id: "organization-1",
      node_type_code: "node_corporate_entity",
      node_id: "organization-1",
      label: "Case main contractor",
      ontology_label: "Organization",
      is_focus: false,
      is_evidence_text_node: true,
    },
    {
      id: "project-1",
      node_type_code: "node_project",
      node_id: "project-1",
      label: "Case grid project",
      ontology_label: "Project",
      is_focus: false,
      is_evidence_text_node: true,
    },
  ],
  edges: [
    {
      source: "post-1",
      target: "team-1",
      edge_type_code: "edge_mention",
      ontology_label: "Mentioned in post",
      confidence: 0.9,
      evidence_post_ids: ["post-1"],
    },
    {
      source: "organization-1",
      target: "project-1",
      edge_type_code: "edge_responsible_for",
      ontology_label: "Responsible for",
      confidence: 0.82,
      evidence_text: "Main contract evidence",
      evidence_post_ids: ["post-1"],
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
  args: { graph: mixedStateGraph, onSelectPost: () => undefined },
};

export const EmptyState: Story = {
  args: {
    graph: { post_id: "post-1", nodes: [], edges: [] },
    onSelectPost: () => undefined,
  },
};
