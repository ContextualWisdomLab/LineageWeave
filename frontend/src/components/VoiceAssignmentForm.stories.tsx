import type { Meta, StoryObj } from "@storybook/react-vite";
import { expect, fn, userEvent, within } from "storybook/test";

import { VoiceAssignmentForm } from "../App";
import "../App.css";

const meta = {
  title: "Post/Connect perspective",
  component: VoiceAssignmentForm,
  args: {
    voices: [
      {
        code: "voc",
        label: "Voice of Customer",
        is_primary: true,
        truth_status_code: "truth_observed",
        evidence_available: false,
      },
    ],
    options: [
      { code: "voc", label: "Voice of Customer" },
      { code: "vops", label: "Voice of Process" },
      { code: "vor", label: "Voice of Regulator" },
    ],
    onSave: fn().mockResolvedValue(undefined),
  },
} satisfies Meta<typeof VoiceAssignmentForm>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Ready: Story = {};

export const Completed: Story = {
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    await userEvent.selectOptions(canvas.getByLabelText("Perspective"), "vops");
    await userEvent.selectOptions(canvas.getByLabelText("Evidence status"), "truth_observed");
    await userEvent.click(canvas.getByRole("button", { name: "Connect perspective" }));
    await expect(canvas.getByRole("status")).toHaveTextContent("Perspective connected.");
  },
};

export const NarrowViewport: Story = {
  parameters: { viewport: { defaultViewport: "mobile1" } },
};
