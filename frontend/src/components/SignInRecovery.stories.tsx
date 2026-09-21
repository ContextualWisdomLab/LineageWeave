import type { Meta, StoryObj } from "@storybook/react-vite";
import { fn } from "storybook/test";
import { SignInRecovery } from "./SignInRecovery";

const meta = {
  title: "Chrome/Sign-in recovery",
  component: SignInRecovery,
  args: {
    brandName: "LineageWeave",
    message: "Sign-in could not be completed. Start again to return to your work.",
    actionLabel: "Start sign-in again",
    onRetry: fn(),
  },
  parameters: { layout: "fullscreen" },
} satisfies Meta<typeof SignInRecovery>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Desktop: Story = {};

export const NarrowViewport: Story = {
  parameters: { viewport: { defaultViewport: "mobile1" } },
};
