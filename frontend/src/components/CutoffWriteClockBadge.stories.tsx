import type { Meta, StoryObj } from "@storybook/react-vite";
import { CutoffWriteClockBadge } from "./CutoffWriteClockBadge";

const meta = {
  title: "AnalysisRun/CutoffWriteClockBadge",
  component: CutoffWriteClockBadge,
} satisfies Meta<typeof CutoffWriteClockBadge>;

export default meta;

type Story = StoryObj<typeof meta>;

export const Default: Story = {};

export const CustomLabel: Story = {
  args: {
    label: "Rewritten after 2026-01-12",
  },
};
