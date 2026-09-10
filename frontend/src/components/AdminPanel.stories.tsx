import type { Meta, StoryObj } from "@storybook/react-vite";
import { fn } from "storybook/test";
import { AdminPanel } from "./AdminPanel";

const meta = {
  title: "Admin/AdminPanel",
  component: AdminPanel,
  args: {
    currentBrandName: "LineageWeave",
    onBrandNameChange: fn(),
    accessToken: "demo-access-token",
  },
} satisfies Meta<typeof AdminPanel>;

export default meta;

type Story = StoryObj<typeof meta>;

export const Default: Story = {};

// Edge case: a long tenant brand name near the input's practical width.
export const LongBrandName: Story = {
  args: {
    currentBrandName: "A Very Long Tenant Brand Name For Layout Testing Purposes",
  },
};
