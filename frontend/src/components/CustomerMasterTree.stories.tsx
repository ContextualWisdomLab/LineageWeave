import type { Meta, StoryObj } from "@storybook/react-vite";
import type { CustomerMasterEntity } from "../api";
import { CustomerMasterTree } from "./CustomerMasterTree";

const hierarchy: CustomerMasterEntity[] = [
  {
    corporate_entity_id: "group-demo",
    corporate_entity_code: "DEMO-GROUP",
    entity_name: "Demo Group",
    entity_level_code: "group",
    entity_level_label: "Group",
    parent_entity_id: null,
  },
  {
    corporate_entity_id: "company-grid",
    corporate_entity_code: "GRID-01",
    entity_name: "Grid Systems",
    entity_level_code: "company",
    entity_level_label: "Company",
    parent_entity_id: "group-demo",
  },
  {
    corporate_entity_id: "plant-east",
    corporate_entity_code: "PLANT-EAST",
    entity_name: "East Plant",
    entity_level_code: "plant",
    entity_level_label: "Plant",
    parent_entity_id: "company-grid",
  },
  {
    corporate_entity_id: "company-energy",
    corporate_entity_code: "ENERGY-01",
    entity_name: "Energy Services",
    entity_level_code: "company",
    entity_level_label: "Company",
    parent_entity_id: "group-demo",
  },
];

const meta = {
  title: "Product/Customer Master/Three Pane Workspace",
  component: CustomerMasterTree,
  parameters: {
    layout: "fullscreen",
  },
  decorators: [
    (Story) => (
      <div style={{ maxWidth: 1440, margin: "0 auto", padding: 24 }}>
        <Story />
      </div>
    ),
  ],
  args: {
    entities: hierarchy,
    initialSelectedEntityId: "company-grid",
    loadRelated: async (entityId: string) => [
      {
        node_id: `post-${entityId}`,
        node_type_code: "node_post",
        relevance: 1,
        label: "Open the latest customer evidence",
        ontology_label: "Post",
        post_body_excerpt: "A source-backed post attached to this customer entity.",
        post_body_truncated: false,
      },
    ],
    onOpenPost: () => undefined,
  },
} satisfies Meta<typeof CustomerMasterTree>;

export default meta;
type Story = StoryObj<typeof meta>;

export const DesktopThreePane: Story = {};

export const PhoneStackedSteps: Story = {
  parameters: {
    viewport: {
      defaultViewport: "mobile1",
    },
  },
};

export const MalformedRelationsRemainVisible: Story = {
  args: {
    initialSelectedEntityId: "orphan",
    entities: [
      {
        ...hierarchy[1],
        corporate_entity_id: "cycle-a",
        entity_name: "Cycle A",
        parent_entity_id: "cycle-b",
      },
      {
        ...hierarchy[1],
        corporate_entity_id: "cycle-b",
        entity_name: "Cycle B",
        parent_entity_id: "cycle-a",
      },
      {
        ...hierarchy[1],
        corporate_entity_id: "orphan",
        entity_name: "Missing visible parent",
        parent_entity_id: "outside-scope",
      },
    ],
  },
};
