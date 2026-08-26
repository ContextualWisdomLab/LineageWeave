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

export const CustomerMaster: Story = {
  args: { destination: "customers" },
};

export const Calendar: Story = {
  args: { destination: "calendar" },
};

export const AskAgent: Story = {
  args: { destination: "ask" },
};

export const WithTools: Story = {
  args: {
    destination: "customers",
    tools: <button type="button">Sign out</button>,
  },
};

export const MobileAllDestinations: Story = {
  args: {
    destination: "dashboard",
    tools: <button type="button">언어</button>,
  },
  globals: { viewport: { value: "mobile1", isRotated: false } },
};
