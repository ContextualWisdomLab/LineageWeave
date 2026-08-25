import type { Meta, StoryObj } from "@storybook/react-vite";
import { expect, within } from "storybook/test";
import { EvidenceStatusMark } from "./EvidenceStatusMark";
import "../App.css";

const meta = {
  title: "Analysis/EvidenceStatusMark",
  component: EvidenceStatusMark,
  parameters: { layout: "padded" },
} satisfies Meta<typeof EvidenceStatusMark>;

export default meta;

type Story = StoryObj<typeof meta>;

export const Evidence: Story = {
  args: { status: "evidence" },
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    const status = canvas.getByRole("status");
    await expect(status).toHaveTextContent("Evidence");
    await expect(status.getAttribute("aria-label")).toMatch(/directly observed/i);
  },
};

export const Inference: Story = {
  args: { status: "inference" },
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    const status = canvas.getByRole("status");
    await expect(status).toHaveTextContent("Inference");
    await expect(status.getAttribute("aria-label")).toMatch(/derived from observed evidence/i);
  },
};

export const Prediction: Story = {
  args: { status: "prediction" },
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    const status = canvas.getByRole("status");
    await expect(status).toHaveTextContent("Prediction");
    // A prediction must never read as settled fact -- it's the whole point
    // of carrying this status through from TEPP ADR 0016 to the UI.
    await expect(status.getAttribute("aria-label")).toMatch(/unconfirmed/i);
  },
};

export const AllThreeSideBySide: Story = {
  render: () => (
    <div style={{ display: "flex", gap: "0.5rem" }}>
      <EvidenceStatusMark status="evidence" />
      <EvidenceStatusMark status="inference" />
      <EvidenceStatusMark status="prediction" />
    </div>
  ),
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    const marks = canvas.getAllByRole("status");
    await expect(marks).toHaveLength(3);
    // Each mark's accessible name must differ -- the non-color
    // distinction requirement (ADR 0132 decision 5) is testable, not
    // just visual.
    const labels = marks.map((mark) => mark.getAttribute("aria-label"));
    await expect(new Set(labels).size).toBe(3);
  },
};
