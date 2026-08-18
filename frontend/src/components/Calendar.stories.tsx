import type { Meta, StoryObj } from "@storybook/react-vite";
import { Calendar } from "./Calendar";

const meta = {
  title: "달력/Calendar",
  component: Calendar,
} satisfies Meta<typeof Calendar>;

export default meta;

type Story = StoryObj<typeof meta>;

export const CalDavUnavailable: Story = {
  args: {
    available: false,
    events: [],
    emptyNextAction: "이 범위의 일정을 아직 받을 수 없습니다",
  },
};
