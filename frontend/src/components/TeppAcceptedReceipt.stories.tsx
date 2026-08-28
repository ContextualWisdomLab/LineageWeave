import type { Meta, StoryObj } from "@storybook/react-vite";
import { expect, within } from "storybook/test";
import { TeppAcceptedReceipt } from "./TeppAcceptedReceipt";
import "../App.css";

const meta = {
  title: "Analysis/TeppAcceptedReceipt",
  component: TeppAcceptedReceipt,
  parameters: { layout: "padded" },
} satisfies Meta<typeof TeppAcceptedReceipt>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Accepted: Story = {
  play: async ({ canvasElement }) => {
    const receipt = within(canvasElement).getByLabelText("Measurement request accepted");
    await expect(receipt).toHaveTextContent("Refresh this run");
    await expect(receipt).not.toHaveTextContent(/TEPP|remote|identifier|succeeded/i);
  },
};
