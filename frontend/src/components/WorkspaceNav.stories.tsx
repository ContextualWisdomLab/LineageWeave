import type { Meta, StoryObj } from "@storybook/react-vite";
import { useState } from "react";
import { expect, userEvent, within } from "storybook/test";
import "../App.css";
import {
  WorkspaceNav,
  type WorkspaceDestination,
  type WorkspaceNavProps,
} from "./WorkspaceNav";

function InteractiveNav(args: WorkspaceNavProps) {
  const [destination, setDestination] = useState<WorkspaceDestination>(
    args.destination,
  );
  return (
    <WorkspaceNav
      {...args}
      destination={destination}
      onChange={(next) => {
        setDestination(next);
        args.onChange(next);
      }}
    />
  );
}

const meta = {
  title: "Workspace/WorkspaceNav",
  component: WorkspaceNav,
  args: {
    destination: "board",
    onChange: () => undefined,
  },
  parameters: { layout: "padded" },
} satisfies Meta<typeof WorkspaceNav>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Desktop: Story = {
  render: (args) => <InteractiveNav {...args} />,
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    await expect(canvas.getByRole("button", { name: "Board" })).toHaveAttribute(
      "aria-current",
      "page",
    );
    await userEvent.click(canvas.getByRole("button", { name: "Ask Agent" }));
    await expect(
      canvas.getByRole("button", { name: "Ask Agent" }),
    ).toHaveAttribute("aria-current", "page");
  },
};

export const PhoneDrawer: Story = {
  args: {
    drawer: true,
    id: "workspace-drawer-story",
    showAdmin: false,
  },
  render: (args) => <InteractiveNav {...args} />,
  parameters: {
    layout: "padded",
    viewport: { defaultViewport: "mobile1" },
  },
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    await expect(
      canvas.getByRole("navigation", { name: "Workspace navigation" }),
    ).toHaveClass("workspace-gnb-drawer");
    await expect(canvas.queryByRole("button", { name: "Admin" })).toBeNull();
  },
};
