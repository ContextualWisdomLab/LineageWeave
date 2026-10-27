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
      "Ask your workspace administrator to enable calendar access. Open a commitment below to read its source post.",
  },
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    const notice = canvas.getByRole("region", { name: /^Unavailable:/ });
    await expect(notice).toHaveTextContent("Unavailable");
    await expect(notice).toHaveTextContent("이 범위의 일정을 아직 받을 수 없습니다");
    await expect(notice).toHaveTextContent("enable calendar access");
    await expect(notice).not.toHaveTextContent(/Naruon|provider|model|transport|environment/i);
    await expect(canvas.queryByRole("alert")).toBeNull();
    await expect(canvas.queryByRole("status")).toBeNull();
  },
};

export const HistoricalBodyUnavailable: Story = {
  args: {
    kind: "unavailable",
    message: "Earlier body unavailable for this date.",
    nextAction: "Read the current body below, then ask the source owner for the earlier version before citing it.",
  },
  play: async ({ canvasElement }) => {
    const notice = within(canvasElement).getByRole("region", { name: /^Unavailable:/ });
    await expect(notice).toHaveTextContent("Earlier body unavailable for this date.");
    await expect(notice).toHaveTextContent("before citing it");
  },
};

export const HistoricalShareUnavailable: Story = {
  args: {
    kind: "unavailable",
    message: "This dated view has no shareable link.",
    nextAction: "To share this post, open its current view first.",
  },
  play: async ({ canvasElement }) => {
    const notice = within(canvasElement).getByRole("region", { name: /^Unavailable:/ });
    await expect(notice).toHaveTextContent("This dated view has no shareable link.");
    await expect(notice).toHaveTextContent("To share this post, open its current view first.");
  },
};

export const HistoricalShareRecovery: Story = {
  args: HistoricalShareUnavailable.args,
  render: (args) => (
    <>
      <div className="post-actions" role="group" aria-label="Post actions">
        <button type="button">Open current view</button>
        <button type="button">Print</button>
        <button type="button">Bookmark</button>
      </div>
      <StatusNotice {...args} />
    </>
  ),
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    await expect(canvas.getByRole("button", { name: "Open current view" })).toBeVisible();
    await expect(canvas.queryByRole("button", { name: "Share" })).toBeNull();
    await expect(canvas.getByRole("region", { name: /^Unavailable:/ })).toHaveTextContent(
      "This dated view has no shareable link.",
    );
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
    await expect(notice).not.toHaveAttribute("aria-label");
    await expect(notice).toHaveTextContent("Retry needed");
    await expect(notice).toHaveTextContent("Dashboard 근거를 불러오지 못했습니다.");
    await userEvent.click(canvas.getByRole("button", { name: "Retry" }));
    await expect(args.onRetry).toHaveBeenCalledTimes(1);
  },
};
