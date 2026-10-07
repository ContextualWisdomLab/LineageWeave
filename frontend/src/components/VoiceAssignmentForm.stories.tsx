import type { Meta, StoryObj } from "@storybook/react-vite";
import { expect, fn, userEvent, within } from "storybook/test";

import { VoiceAssignmentForm } from "../App";
import { BackendError } from "../api";
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
    await expect(canvas.getByRole("region", { name: /Ready:/ })).toHaveTextContent("Perspective connected.");
  },
};

export const NarrowViewport: Story = {
  parameters: { viewport: { defaultViewport: "mobile1" } },
};

export const RetryableFailure: Story = {
  args: { onSave: async () => { throw new Error("synthetic private detail"); } },
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    await userEvent.selectOptions(canvas.getByLabelText("Perspective"), "vops");
    await userEvent.selectOptions(canvas.getByLabelText("Evidence status"), "truth_observed");
    await userEvent.click(canvas.getByRole("button", { name: "Connect perspective" }));
    await expect(canvas.getByRole("alert")).toHaveTextContent("Review your selections");
    await expect(canvas.queryByText(/synthetic private detail/)).not.toBeInTheDocument();
  },
};

export const SignInRequired: Story = {
  args: { onSave: async () => { throw new BackendError("/synthetic", 401); } },
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    await userEvent.selectOptions(canvas.getByLabelText("Perspective"), "vor");
    await userEvent.selectOptions(canvas.getByLabelText("Evidence status"), "truth_proposed");
    await userEvent.click(canvas.getByRole("button", { name: "Connect perspective" }));
    await expect(canvas.getByRole("region", { name: /Unavailable:/ })).toHaveTextContent("Sign in again, then reopen this post.");
    await expect(canvas.getByRole("button", { name: "Connect perspective" })).toBeDisabled();
  },
};
