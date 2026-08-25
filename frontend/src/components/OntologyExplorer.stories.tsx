import type { Meta, StoryObj } from "@storybook/react-vite";
import type { OntologyNeighborhoodPayload } from "../api";
import { OntologyExplorer } from "./OntologyExplorer";

const POST_ID = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa1";
const PERSON_ID = "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbb1";
const CORP_ID = "cccccccc-cccc-cccc-cccc-ccccccccccc1";
const PROJECT_ID = "demo-project";

const demoNeighborhood: OntologyNeighborhoodPayload = {
  focus_node_id: POST_ID,
  focus_node_type_code: "node_post",
  truncated: false,
  next_cursor: null,
  limitation_code: null,
  nodes: [
    {
      node_id: POST_ID,
      node_type_code: "node_post",
      ontology_class_iri: "https://contextualwisdomlab.github.io/LineageWeave/ontology#Post",
      display_label: "Demo public post",
      truth_status_code: "truth_observed",
      valid_from: null,
      valid_to: null,
      recorded_at: "2026-01-10T12:00:00+00:00",
      evidence_count: 1,
      shape_code: "rectangle",
    },
    {
      node_id: PERSON_ID,
      node_type_code: "node_person",
      ontology_class_iri: "https://contextualwisdomlab.github.io/LineageWeave/ontology#Person",
      display_label: "Test Person",
      truth_status_code: "truth_observed",
      valid_from: null,
      valid_to: null,
      recorded_at: "2026-01-10T12:00:00+00:00",
      evidence_count: 1,
      shape_code: "ellipse",
    },
    {
      node_id: CORP_ID,
      node_type_code: "node_corporate_entity",
      ontology_class_iri: "https://contextualwisdomlab.github.io/LineageWeave/ontology#CorporateEntity",
      display_label: "Demo Corp",
      truth_status_code: "truth_observed",
      valid_from: null,
      valid_to: null,
      recorded_at: "2026-01-10T12:00:00+00:00",
      evidence_count: 1,
      shape_code: "hexagon",
    },
    {
      node_id: PROJECT_ID,
      node_type_code: "node_project",
      ontology_class_iri: "https://contextualwisdomlab.github.io/LineageWeave/ontology#Project",
      display_label: "Demo Project",
      truth_status_code: "truth_proposed",
      valid_from: null,
      valid_to: null,
      recorded_at: "2026-01-10T12:00:00+00:00",
      evidence_count: 1,
      shape_code: "diamond",
    },
  ],
  edges: [
    {
      edge_id: `mentions:node_post:${POST_ID}:node_person:${PERSON_ID}`,
      source_node_type_code: "node_post",
      source_node_id: POST_ID,
      target_node_type_code: "node_person",
      target_node_id: PERSON_ID,
      property_code: "mentions",
      ontology_property_iri: "https://contextualwisdomlab.github.io/LineageWeave/ontology#mentions",
      property_label: "mentions",
      truth_status_code: "truth_observed",
      valid_from: null,
      valid_to: null,
      recorded_at: "2026-01-10T12:00:00+00:00",
      provenance_reference: "knowledge_graph_edge",
      evidence_references: [POST_ID],
    },
    {
      edge_id: `affiliatedWith:node_person:${PERSON_ID}:node_corporate_entity:${CORP_ID}`,
      source_node_type_code: "node_person",
      source_node_id: PERSON_ID,
      target_node_type_code: "node_corporate_entity",
      target_node_id: CORP_ID,
      property_code: "affiliatedWith",
      ontology_property_iri: "https://contextualwisdomlab.github.io/LineageWeave/ontology#affiliatedWith",
      property_label: "affiliated with",
      truth_status_code: "truth_observed",
      valid_from: null,
      valid_to: null,
      recorded_at: "2026-01-10T12:00:00+00:00",
      provenance_reference: "knowledge_graph_edge",
      evidence_references: [POST_ID],
    },
    {
      edge_id: `mentionsProject:node_post:${POST_ID}:node_project:${PROJECT_ID}`,
      source_node_type_code: "node_post",
      source_node_id: POST_ID,
      target_node_type_code: "node_project",
      target_node_id: PROJECT_ID,
      property_code: "mentionsProject",
      ontology_property_iri: "https://contextualwisdomlab.github.io/LineageWeave/ontology#mentionsProject",
      property_label: "mentions project",
      truth_status_code: "truth_proposed",
      valid_from: null,
      valid_to: null,
      recorded_at: "2026-01-10T12:00:00+00:00",
      provenance_reference: "post_project_mention",
      evidence_references: [POST_ID],
    },
  ],
  exact_value_rows: [
    {
      edge_id: `mentions:node_post:${POST_ID}:node_person:${PERSON_ID}`,
      source_node_id: POST_ID,
      source_label: "Demo public post",
      source_type_code: "node_post",
      property_code: "mentions",
      property_label: "mentions",
      ontology_property_iri: "https://contextualwisdomlab.github.io/LineageWeave/ontology#mentions",
      target_node_id: PERSON_ID,
      target_label: "Test Person",
      target_type_code: "node_person",
      truth_status_code: "truth_observed",
      recorded_at: "2026-01-10T12:00:00+00:00",
      valid_from: "",
      valid_to: "",
      evidence_count: "1",
    },
    {
      edge_id: `affiliatedWith:node_person:${PERSON_ID}:node_corporate_entity:${CORP_ID}`,
      source_node_id: PERSON_ID,
      source_label: "Test Person",
      source_type_code: "node_person",
      property_code: "affiliatedWith",
      property_label: "affiliated with",
      ontology_property_iri: "https://contextualwisdomlab.github.io/LineageWeave/ontology#affiliatedWith",
      target_node_id: CORP_ID,
      target_label: "Demo Corp",
      target_type_code: "node_corporate_entity",
      truth_status_code: "truth_observed",
      recorded_at: "2026-01-10T12:00:00+00:00",
      valid_from: "",
      valid_to: "",
      evidence_count: "1",
    },
    {
      edge_id: `mentionsProject:node_post:${POST_ID}:node_project:${PROJECT_ID}`,
      source_node_id: POST_ID,
      source_label: "Demo public post",
      source_type_code: "node_post",
      property_code: "mentionsProject",
      property_label: "mentions project",
      ontology_property_iri: "https://contextualwisdomlab.github.io/LineageWeave/ontology#mentionsProject",
      target_node_id: PROJECT_ID,
      target_label: "Demo Project",
      target_type_code: "node_project",
      truth_status_code: "truth_proposed",
      recorded_at: "2026-01-10T12:00:00+00:00",
      valid_from: "",
      valid_to: "",
      evidence_count: "1",
    },
  ],
  jsonld: {
    "@context": { lw: "https://contextualwisdomlab.github.io/LineageWeave/ontology#" },
    "@graph": [],
  },
};

const emptyNeighborhood: OntologyNeighborhoodPayload = {
  ...demoNeighborhood,
  edges: [],
  exact_value_rows: [],
  nodes: [demoNeighborhood.nodes[0]],
  limitation_code: "neighborhood_empty",
};

const truncatedNeighborhood: OntologyNeighborhoodPayload = {
  ...demoNeighborhood,
  truncated: true,
  next_cursor: "after:mentions",
  limitation_code: "neighborhood_truncated",
  edges: [demoNeighborhood.edges[0]],
  exact_value_rows: [demoNeighborhood.exact_value_rows[0]],
};

const partialNeighborhood: OntologyNeighborhoodPayload = {
  ...demoNeighborhood,
  nodes: demoNeighborhood.nodes.slice(0, 2),
  edges: [demoNeighborhood.edges[0]],
  exact_value_rows: [demoNeighborhood.exact_value_rows[0]],
  limitation_code: null,
};

const rejectedNeighborhood: OntologyNeighborhoodPayload = {
  ...demoNeighborhood,
  edges: [
    {
      ...demoNeighborhood.edges[1],
      truth_status_code: "truth_rejected",
    },
  ],
  exact_value_rows: [
    {
      ...demoNeighborhood.exact_value_rows[1],
      truth_status_code: "truth_rejected",
    },
  ],
};

const meta = {
  title: "Evidence/OntologyExplorer",
  component: OntologyExplorer,
  args: {
    focusNodeType: "node_post",
    focusNodeId: POST_ID,
    neighborhood: demoNeighborhood,
  },
} satisfies Meta<typeof OntologyExplorer>;

export default meta;

type Story = StoryObj<typeof meta>;

export const DesktopNeighborhood: Story = {};

export const NarrowExactValue: Story = {
  globals: {
    viewport: { value: "mobile1", isRotated: false },
  },
  decorators: [
    (Story) => (
      <div style={{ maxWidth: 420 }}>
        <Story />
      </div>
    ),
  ],
};

export const NodeDrawer: Story = {
  play: ({ canvasElement }) => {
    const node = [...canvasElement.querySelectorAll("[role=button]")].find((element) =>
      element.getAttribute("aria-label")?.startsWith("Select node:"),
    );
    if (!node) throw new Error("Ontology node control was not rendered");
    node.dispatchEvent(new MouseEvent("click", { bubbles: true }));
  },
};

export const EdgeDrawer: Story = {
  play: ({ canvasElement }) => {
    const edge = [...canvasElement.querySelectorAll("[role=button]")].find((element) =>
      element.getAttribute("aria-label")?.startsWith("Select edge:"),
    );
    if (!edge) throw new Error("Ontology edge control was not rendered");
    edge.dispatchEvent(new MouseEvent("click", { bubbles: true }));
  },
};

export const LegendAndFilter: Story = {
  play: ({ canvasElement }) => {
    const search = canvasElement.querySelector<HTMLInputElement>(
      'input[aria-label="Search within this neighborhood"]',
    );
    if (!search) throw new Error("Ontology search control was not rendered");
    const setValue = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, "value")?.set;
    setValue?.call(search, "Priya");
    search.dispatchEvent(new Event("input", { bubbles: true }));
  },
};

export const Empty: Story = {
  args: {
    neighborhood: emptyNeighborhood,
    status: "empty",
  },
};

export const Truncated: Story = {
  args: {
    neighborhood: truncatedNeighborhood,
    status: "truncated",
  },
};

export const Partial: Story = {
  args: {
    neighborhood: partialNeighborhood,
    status: "ready",
  },
};

export const Denied: Story = {
  args: {
    neighborhood: null,
    status: "denied",
  },
};

export const StaleCutoff: Story = {
  args: {
    knowledgeCutoff: "2026-01-15T12:00:00Z",
    status: "stale",
  },
};

export const RejectedProposal: Story = {
  args: {
    neighborhood: rejectedNeighborhood,
    status: "rejected",
  },
};
