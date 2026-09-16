import type { Meta, StoryObj } from "@storybook/react-vite";
import { fn } from "storybook/test";
import { PopupCloseButton } from "./PopupCloseButton";

const meta = {
  title: "Chrome/PopupCloseButton",
  component: PopupCloseButton,
  args: {
    label: "Close evidence panel",
    onClose: fn(),
  },
} satisfies Meta<typeof PopupCloseButton>;

export default meta;

type Story = StoryObj<typeof meta>;

export const EvidencePanel: Story = {};

export const PostPopup: Story = {
  args: {
    label: "Close",
  },
};
