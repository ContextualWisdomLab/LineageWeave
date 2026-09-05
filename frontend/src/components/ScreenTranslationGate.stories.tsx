import type { Meta, StoryObj } from "@storybook/react-vite";
import { ScreenTranslationGate } from "./ScreenTranslationGate";

const meta = {
  title: "Chrome/Screen translation gate",
  component: ScreenTranslationGate,
  args: { onRetry: () => undefined },
} satisfies Meta<typeof ScreenTranslationGate>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Loading: Story = { args: { state: "loading" } };
export const Retry: Story = { args: { state: "retry" } };
export const RetryMobile: Story = {
  args: { state: "retry" },
  parameters: { viewport: { defaultViewport: "mobile1" } },
};
