import type { Meta, StoryObj } from "@storybook/react-vite";
import { expect, within } from "storybook/test";
import { CustomerEntityTreeRow } from "./App";
import { buildCustomerEntityTree } from "./customerEntityTree";
import type { CustomerMasterEntity } from "./api";

function entity(
  id: string,
  parent: string | null,
  name = id,
): CustomerMasterEntity {
  return {
    corporate_entity_id: id,
    entity_name: name,
    corporate_entity_code: id,
    entity_level_code: "L",
    entity_level_label: "Level",
    parent_entity_id: parent,
  };
}

const callbacks = {
  onToggle: () => undefined,
  onOpenPost: () => undefined,
};

const meta = {
  title: "Customers/EntityTreeRow",
  component: CustomerEntityTreeRow,
} satisfies Meta<typeof CustomerEntityTreeRow>;
export default meta;
type Story = StoryObj<typeof meta>;

function ForestList({ nodes }: { nodes: ReturnType<typeof buildCustomerEntityTree> }) {
  return (
    <ul>
      {nodes.map((node) => (
        <CustomerEntityTreeRow
          key={node.entity.corporate_entity_id}
          node={node}
          depth={0}
          expandedEntityId={null}
          relatedByEntity={{}}
          relatedLoading={null}
          {...callbacks}
        />
      ))}
    </ul>
  );
}

export const PureCycle: Story = {
  render: () => (
    <ForestList
      nodes={buildCustomerEntityTree([
        entity("A", "B", "Alpha"),
        entity("B", "A", "Beta"),
      ])}
    />
  ),
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    await expect(canvas.getByText("Alpha")).toBeInTheDocument();
    await expect(canvas.getByText("Beta")).toBeInTheDocument();
    await expect(
      canvas.getByText("Shown as top level: listed parent forms a cycle."),
    ).toBeInTheDocument();
  },
};

export const SelfParent: Story = {
  render: () => (
    <ForestList nodes={buildCustomerEntityTree([entity("S", "S", "Solo")])} />
  ),
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    await expect(canvas.getByText("Solo")).toBeInTheDocument();
    await expect(
      canvas.getByText("Shown as top level: entity lists itself as parent."),
    ).toBeInTheDocument();
  },
};

export const UnlistedParent: Story = {
  render: () => (
    <ForestList
      nodes={buildCustomerEntityTree([entity("child", "ghost", "Orphan")])}
    />
  ),
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    await expect(canvas.getByText("Orphan")).toBeDefined();
    await expect(
      canvas.getByText("Shown as top level: listed parent is not visible."),
    ).toBeInTheDocument();
  },
};
