import type { Meta, StoryObj } from "@storybook/react-vite";
import { SummaryStatus } from "./SummaryStatus";
import "../App.css";

const meta = {
  title: "Evidence/SummaryStatus",
  component: SummaryStatus,
  parameters: { layout: "padded" },
  args: {
    kind: "processing",
    title: "Summary is being prepared.",
    description: "The source evidence is still being analyzed.",
  },
} satisfies Meta<typeof SummaryStatus>;

export default meta;

type Story = StoryObj<typeof meta>;

export const Processing: Story = {};

export const Unavailable: Story = {
  args: {
    kind: "unavailable",
    title: "Summary could not be generated.",
    description: "The source record remains available.",
    detail: "Try again when the analysis service is available.",
    retryLabel: "Retry summary",
    onRetry: () => undefined,
  },
};

export const Empty: Story = {
  args: {
    kind: "empty",
    title: "No saved summary exists for this record.",
    description: "The source record is available, but no summary has been saved.",
    retryLabel: "Retry summary",
    onRetry: () => undefined,
  },
};
