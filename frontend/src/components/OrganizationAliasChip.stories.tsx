import type { Meta, StoryObj } from "@storybook/react-vite";
import { OrganizationAliasChip } from "./OrganizationAliasChip";

const meta = {
  title: "Evidence/OrganizationAliasChip",
  component: OrganizationAliasChip,
  args: {
    displayName: "Demo Corp",
    ariaLabel: "Affiliate org: Demo Corp",
    onSelect: () => undefined,
  },
} satisfies Meta<typeof OrganizationAliasChip>;

export default meta;

type Story = StoryObj<typeof meta>;

export const CatalogName: Story = {};

export const WithCompanion: Story = {
  args: {
    organizationAlias: "DC",
    ariaLabel: "Affiliate org: Demo Corp (DC)",
  },
};

export const Unlabeled: Story = {
  args: {
    displayName: "Northridge Grid",
    organizationAlias: undefined,
    ariaLabel: "Affiliate org: Northridge Grid",
  },
};
