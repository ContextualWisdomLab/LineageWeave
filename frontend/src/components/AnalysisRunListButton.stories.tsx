import type { Meta, StoryObj } from "@storybook/react-vite";
import { AnalysisRunListButton } from "./AnalysisRunListButton";

const meta = {
  title: "AnalysisRuns/ListButton",
  component: AnalysisRunListButton,
  args: {
    caption: "Lineage reconstruction · Pending · Demo Corp",
    nextAction:
      "Open this run to confirm which posts it will use. Reconstruction has not started yet.",
    documentCountLabel: "3 documents",
    onOpen: () => undefined,
  },
} satisfies Meta<typeof AnalysisRunListButton>;

export default meta;

type Story = StoryObj<typeof meta>;

export const PendingLineage: Story = {};

export const FailedTepp: Story = {
  args: {
    caption: "TEPP measurement · Failed · Demo Corp",
    nextAction:
      "Open this run to see why it failed, then connect the measurement service and re-run.",
    documentCountLabel: "3 documents",
  },
};

export const PendingTepp: Story = {
  args: {
    caption: "TEPP measurement · Pending · Demo Corp",
    nextAction:
      "Open this run to confirm which posts TEPP will measure. Measurement has not started yet — this is not a calibrated result.",
  },
};
