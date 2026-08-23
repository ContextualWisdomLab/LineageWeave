import type { Meta, StoryObj } from "@storybook/react-vite";
import { CutoffKnownBody } from "./CutoffKnownBody";

const meta = {
  title: "AnalysisRun/CutoffKnownBody",
  component: CutoffKnownBody,
  args: {
    title: "Demo public post",
    body: "Ada West at Demo Corp followed up with Priya Nair at Northridge Grid about the delayed shipment.",
    writtenAt: "2026-01-10T12:00:00Z",
    cutoff: "2026-01-12T12:00:00Z",
  },
} satisfies Meta<typeof CutoffKnownBody>;

export default meta;

type Story = StoryObj<typeof meta>;

export const Default: Story = {};

export const BothClocks: Story = {
  args: {
    title: "Public post",
    body: "The cutoff body this run knew.",
    writtenAt: "2026-01-10T12:00:00Z",
    cutoff: "2026-01-12T12:00:00Z",
  },
};
