import type { Meta, StoryObj } from "@storybook/react-vite";
import { expect, within } from "storybook/test";
import { TeppAcceptedReceipt } from "./TeppAcceptedReceipt";
import "../App.css";

const meta = {
  title: "Analysis/TeppAcceptedReceipt",
  component: TeppAcceptedReceipt,
  args: { remoteRunId: "tepp-run-synthetic-001" },
  parameters: { layout: "padded" },
} satisfies Meta<typeof TeppAcceptedReceipt>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Accepted: Story = {
  play: async ({ canvasElement }) => {
    const receipt = within(canvasElement).getByLabelText("TEPP accepted receipt");
    await expect(receipt).toHaveTextContent("tepp-run-synthetic-001");
    await expect(receipt).not.toHaveTextContent(/measurement|succeeded/i);
  },
};
