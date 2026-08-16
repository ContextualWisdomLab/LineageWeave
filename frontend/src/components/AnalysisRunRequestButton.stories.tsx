import type { Meta, StoryObj } from "@storybook/react-vite";
import { AnalysisRunRequestButton } from "./AnalysisRunRequestButton";

const meta = {
  title: "AnalysisRuns/RequestButton",
  component: AnalysisRunRequestButton,
  args: {
    requesting: false,
    onRequest: () => undefined,
  },
} satisfies Meta<typeof AnalysisRunRequestButton>;

export default meta;

type Story = StoryObj<typeof meta>;

export const Idle: Story = {};

export const Recording: Story = {
  args: {
    requesting: true,
  },
};
