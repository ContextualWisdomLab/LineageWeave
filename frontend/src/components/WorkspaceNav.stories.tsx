import type { Meta, StoryObj } from "@storybook/react-vite";
import { WorkspaceNav } from "./WorkspaceNav";

const meta = {
  title: "Navigation/WorkspaceNav",
  component: WorkspaceNav,
  args: {
    destination: "board",
    onChange: () => undefined,
  },
} satisfies Meta<typeof WorkspaceNav>;

export default meta;

type Story = StoryObj<typeof meta>;

export const Board: Story = {};

export const AskAgent: Story = {
  args: { destination: "ask" },
};

export const Admin: Story = {
  args: { destination: "admin" },
};

// Edge case: an extra tools slot (e.g. a settings or logout control) rendered
// alongside the nav items.
export const WithTools: Story = {
  args: {
    destination: "customers",
    tools: <button type="button">Sign out</button>,
  },
};
