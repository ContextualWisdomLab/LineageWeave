import type { Meta, StoryObj } from "@storybook/react-vite";
import { GroundedQa } from "./GroundedQa";

const meta = {
  title: "Ask Cubee/GroundedQa",
  component: GroundedQa,
  args: {
    onAsk: async (question: string) => ({
      question,
      slot_code: "who",
      values: ["Ada West"],
      grounded: true,
      empty_next_action: null,
    }),
  },
} satisfies Meta<typeof GroundedQa>;

export default meta;

type Story = StoryObj<typeof meta>;

export const Ready: Story = {};
