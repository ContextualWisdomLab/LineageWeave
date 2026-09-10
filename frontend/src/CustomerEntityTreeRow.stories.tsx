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

// Reuse LineageWeave's existing Storybook viewport presets so malformed
// hierarchy acceptance can be exercised at desktop, mobile, and the principal
// intermediate width without inventing a second responsive-test vocabulary.
export const PureCycleMobile: Story = {
  ...PureCycle,
  globals: { viewport: { value: "mobile1", isRotated: false } },
};

export const PureCycleIntermediate: Story = {
  ...PureCycle,
  globals: { viewport: { value: "tablet", isRotated: false } },
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

export const OrdinaryTree: Story = {
  render: () => (
    <ForestList
      nodes={buildCustomerEntityTree([
        entity("root", null, "Root"),
        entity("kid", "root", "Kid"),
      ])}
    />
  ),
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    await expect(canvas.getByText("Root")).toBeInTheDocument();
    await expect(canvas.getByText("Kid")).toBeInTheDocument();
    await expect(
      canvas.queryByText("Shown as top level: listed parent forms a cycle."),
    ).not.toBeInTheDocument();
    await expect(
      canvas.queryByText("Shown as top level: entity lists itself as parent."),
    ).not.toBeInTheDocument();
    await expect(
      canvas.queryByText("Shown as top level: listed parent is not visible."),
    ).not.toBeInTheDocument();
  },
};

export const LoadingRelatedPosts: Story = {
  render: () => {
    const [node] = buildCustomerEntityTree([entity("root", null, "Root")]);
    return (
      <ul>
        <CustomerEntityTreeRow
          node={node}
          depth={0}
          expandedEntityId="root"
          relatedByEntity={{}}
          relatedLoading="root"
          {...callbacks}
        />
      </ul>
    );
  },
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    await expect(canvas.getByRole("status")).toHaveTextContent("Loading related posts...");
    await expect(canvas.queryByText("No linked posts yet.")).not.toBeInTheDocument();
  },
};

export const EmptyRelatedPosts: Story = {
  render: () => {
    const [node] = buildCustomerEntityTree([entity("root", null, "Root")]);
    return (
      <ul>
        <CustomerEntityTreeRow
          node={node}
          depth={0}
          expandedEntityId="root"
          relatedByEntity={{ root: [] }}
          relatedLoading={null}
          {...callbacks}
        />
      </ul>
    );
  },
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    await expect(canvas.getByText("No linked posts yet.")).toBeInTheDocument();
    await expect(canvas.queryByRole("status")).not.toBeInTheDocument();
  },
};
