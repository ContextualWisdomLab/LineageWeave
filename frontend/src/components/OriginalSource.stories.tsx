import type { Meta, StoryObj } from "@storybook/react-vite";
import { OriginalSource } from "./OriginalSource";

const meta = {
  title: "사건 lineage/OriginalSource",
  component: OriginalSource,
} satisfies Meta<typeof OriginalSource>;

export default meta;

type Story = StoryObj<typeof meta>;

export const PlainText: Story = {
  args: {
    body: "The full body text.",
  },
};
