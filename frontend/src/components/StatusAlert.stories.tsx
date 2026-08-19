import type { Meta, StoryObj } from "@storybook/react-vite";
import { StatusAlert } from "./StatusAlert";

const meta = {
  title: "Chrome/StatusAlert",
  component: StatusAlert,
  args: {
    children:
      "This run is not on your list. Open a visible run from the home list, or request a lineage reconstruction for a corporation you already walk.",
  },
} satisfies Meta<typeof StatusAlert>;

export default meta;

type Story = StoryObj<typeof meta>;

export const HiddenAnalysisRun: Story = {};

export const ListLoadFailure: Story = {
  args: {
    children: "BackendError: 503 Service Unavailable",
  },
};
