import type { Meta, StoryObj } from "@storybook/react-vite";
import { expect, within } from "storybook/test";
import { SurfaceBoundary } from "./App";

const pending = new Promise<never>(() => undefined);

function DeferredSurface() {
  throw pending;
}

function FailedSurface() {
  throw new Error("synthetic chunk failure");
}

const meta = {
  title: "Workspace/SurfaceBoundary",
  component: SurfaceBoundary,
} satisfies Meta<typeof SurfaceBoundary>;
export default meta;
type Story = StoryObj<typeof meta>;

export const Loading: Story = {
  args: { children: <DeferredSurface /> },
  play: async ({ canvasElement }) => {
    await expect(within(canvasElement).getByRole("status")).toHaveTextContent("Loading...");
  },
};

export const LoadError: Story = {
  args: { children: <FailedSurface /> },
  play: async ({ canvasElement }) => {
    await expect(within(canvasElement).getByRole("alert")).toHaveTextContent(
      "This view is unavailable. Refresh once; if it fails again, contact your administrator.",
    );
    await expect(within(canvasElement).getByRole("button", { name: "Refresh" })).toBeInTheDocument();
  },
};
