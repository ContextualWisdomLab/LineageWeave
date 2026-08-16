import type { Meta, StoryObj } from "@storybook/react-vite";
import type { RelatedNode } from "./api";
import { RelatedNodeChip } from "./RelatedNodeChip";

function node(partial: Partial<RelatedNode> & Pick<RelatedNode, "node_type_code">): RelatedNode {
  return {
    node_id: "node-1",
    relevance: 0.4,
    ...partial,
  };
}

const meta = {
  title: "Walk/RelatedNodeChip",
  component: RelatedNodeChip,
  parameters: {
    docs: {
      description: {
        component:
          "Click a person or organization chip to continue the Keyman walk. When the caption says multiple organizations, open the Keyman list. Click a post chip to open that source.",
      },
    },
  },
} satisfies Meta<typeof RelatedNodeChip>;

export default meta;
type Story = StoryObj<typeof meta>;

export const UniqueAffiliation: Story = {
  args: {
    node: node({
      node_type_code: "node_person",
      label: "Ada West",
      person_side_label: "Our side",
      affiliation_organization_name: "Demo Corp",
    }),
    onSelect: () => undefined,
  },
};

export const PluralAffiliations: Story = {
  args: {
    node: node({
      node_type_code: "node_person",
      label: "Priya Nair",
      person_side_label: "Counterparty",
      affiliation_ambiguous: true,
    }),
    onSelect: () => undefined,
  },
};

export const MissingAffiliation: Story = {
  args: {
    node: node({
      node_type_code: "node_person",
      label: "Priya Nair",
      person_side_label: "Counterparty",
    }),
    onSelect: () => undefined,
  },
};

export const OrganizationLevel: Story = {
  args: {
    node: node({
      node_type_code: "node_corporate_entity",
      label: "Demo Corp",
      entity_level_label: "Company",
    }),
    onSelect: () => undefined,
  },
};

export const RelatedPost: Story = {
  args: {
    node: node({
      node_type_code: "node_post",
      label: "Linked post",
      ontology_label: "Post",
    }),
    onSelect: () => undefined,
  },
};
