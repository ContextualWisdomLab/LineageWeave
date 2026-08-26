import type { Meta, StoryObj } from "@storybook/react-vite";
import { expect, within } from "storybook/test";
import { CustomerLinkingGuidance } from "./App";
import "./App.css";

const meta = {
  title: "Customer Master/Linking guidance",
  component: CustomerLinkingGuidance,
  parameters: { layout: "padded" },
} satisfies Meta<typeof CustomerLinkingGuidance>;

export default meta;
type Story = StoryObj<typeof meta>;

async function verifyCustomerAction(canvasElement: HTMLElement) {
  const canvas = within(canvasElement);
  await expect(
    canvas.getByText(
      "Before linking a customer, compare the source identifier with the related posts and organization evidence.",
    ),
  ).toBeVisible();
  await expect(
    canvas.queryByText(/ontology|semantic evidence|provider|transport/i),
  ).not.toBeInTheDocument();
}

export const Desktop: Story = {
  play: ({ canvasElement }) => verifyCustomerAction(canvasElement),
};

export const Narrow: Story = {
  parameters: { viewport: { defaultViewport: "mobile1" } },
  play: ({ canvasElement }) => verifyCustomerAction(canvasElement),
};
