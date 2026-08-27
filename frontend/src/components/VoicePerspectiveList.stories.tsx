import type { Meta, StoryObj } from "@storybook/react-vite";
import { expect, within } from "storybook/test";

import { VoicePerspectiveList } from "../App";
import "../App.css";

const meta = {
  title: "Post/Recorded perspectives",
  component: VoicePerspectiveList,
  args: {
    voices: [
      {
        code: "voc",
        label: "Voice of Customer",
        is_primary: true,
        truth_status_code: "truth_observed",
        evidence_available: false,
      },
      {
        code: "vops",
        label: "Voice of Process",
        is_primary: false,
        truth_status_code: "truth_observed",
        evidence_available: true,
      },
    ],
  },
} satisfies Meta<typeof VoicePerspectiveList>;

export default meta;
type Story = StoryObj<typeof meta>;

export const CombinedEvidence: Story = {
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    await expect(canvas.getByText("Imported from source")).toBeVisible();
    await expect(canvas.getByText("Evidence connected")).toBeVisible();
  },
};

export const NarrowViewport: Story = {
  parameters: { viewport: { defaultViewport: "mobile1" } },
};

export const RejectedEvidence: Story = {
  args: {
    voices: [
      ...meta.args.voices,
      {
        code: "vor",
        label: "Voice of Regulator",
        is_primary: false,
        truth_status_code: "truth_rejected",
        evidence_available: true,
      },
    ],
  },
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    await expect(canvas.getByText("Voice of Regulator (Rejected)")).toBeVisible();
  },
};
