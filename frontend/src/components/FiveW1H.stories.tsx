import type { Meta, StoryObj } from "@storybook/react-vite";
import { FiveW1H } from "./FiveW1H";

const meta = {
  title: "게시판/FiveW1H",
  component: FiveW1H,
} satisfies Meta<typeof FiveW1H>;

export default meta;

type Story = StoryObj<typeof meta>;

export const SeededSlots: Story = {
  args: {
    slots: [
      { slot_code: "who", slot_label: "누가", values: ["Ada West"], empty_next_action: null },
      { slot_code: "what", slot_label: "무엇을", values: ["현장 방문"], empty_next_action: null },
      { slot_code: "when", slot_label: "언제", values: ["2026-01-01"], empty_next_action: null },
      { slot_code: "where", slot_label: "어디서", values: ["Demo Corp"], empty_next_action: null },
      {
        slot_code: "why",
        slot_label: "왜",
        values: [],
        empty_next_action: "이 사건의 왜가 아직 없습니다",
      },
      {
        slot_code: "how",
        slot_label: "어떻게",
        values: [],
        empty_next_action: "이 사건의 어떻게가 아직 없습니다",
      },
    ],
  },
};
