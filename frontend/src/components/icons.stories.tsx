import type { Meta, StoryObj } from "@storybook/react-vite";
import { CloseIcon, MenuIcon, SendIcon } from "./icons";

function IconGallery() {
  return (
    <div style={{ display: "flex", gap: "1.5rem", fontSize: "2rem" }}>
      <span title="MenuIcon"><MenuIcon /></span>
      <span title="CloseIcon"><CloseIcon /></span>
      <span title="SendIcon"><SendIcon /></span>
    </div>
  );
}

const meta = {
  title: "Workspace/Icons",
  component: IconGallery,
  parameters: { layout: "padded" },
} satisfies Meta<typeof IconGallery>;

export default meta;

type Story = StoryObj<typeof meta>;

export const Gallery: Story = {};
