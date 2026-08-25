import type { Meta, StoryObj } from "@storybook/react-vite";
import { expect, fn, userEvent, within } from "storybook/test";
import { StatusNotice } from "./StatusNotice";
import "../App.css";

const meta = {
  title: "Chrome/StatusNotice",
  component: StatusNotice,
  parameters: { layout: "padded" },
} satisfies Meta<typeof StatusNotice>;

export default meta;

type Story = StoryObj<typeof meta>;

export const Success: Story = {
  args: {
    kind: "success",
    message: "Observed calendar events are ready. Open a commitment to read that post.",
  },
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    const notice = canvas.getByRole("region", { name: /^Ready:/ });
    await expect(notice).toHaveTextContent("Ready");
    await expect(notice.getAttribute("aria-label")).toMatch(/ready to use/i);
    await expect(canvas.queryByRole("button")).toBeNull();
    await expect(canvas.queryByRole("status")).toBeNull();
  },
};

export const Unavailable: Story = {
  args: {
    kind: "unavailable",
    message: "이 범위의 일정을 아직 받을 수 없습니다",
    nextAction:
      "Connect the Naruon calendar projection. Open a commitment below to read that post.",
  },
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    const notice = canvas.getByRole("region", { name: /^Unavailable:/ });
    await expect(notice).toHaveTextContent("Unavailable");
    await expect(notice).toHaveTextContent("이 범위의 일정을 아직 받을 수 없습니다");
    await expect(notice).toHaveTextContent("Connect the Naruon calendar projection");
    await expect(canvas.queryByRole("alert")).toBeNull();
    await expect(canvas.queryByRole("status")).toBeNull();
  },
};

export const Retry: Story = {
  args: {
    kind: "retry",
    message: "Dashboard 근거를 불러오지 못했습니다.",
    onRetry: fn(),
  },
  play: async ({ canvasElement, args }) => {
    const canvas = within(canvasElement);
    const notice = canvas.getByRole("alert");
    await expect(notice).toHaveTextContent("Retry needed");
    await userEvent.click(canvas.getByRole("button", { name: "Retry" }));
    await expect(args.onRetry).toHaveBeenCalledTimes(1);
  },
};
