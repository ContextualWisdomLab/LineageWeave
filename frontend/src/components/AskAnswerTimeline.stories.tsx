import type { Meta, StoryObj } from "@storybook/react-vite";
import { expect, userEvent, within } from "storybook/test";
import { AskAnswerTimeline } from "./AskAnswerTimeline";
import "../App.css";

const meta = {
  title: "Ask Agent/AnswerEvidenceTimeline",
  component: AskAnswerTimeline,
  parameters: { layout: "fullscreen" },
  decorators: [(Story) => <div className="workspace-destination"><Story /></div>],
} satisfies Meta<typeof AskAnswerTimeline>;
export default meta;
type Story = StoryObj<typeof meta>;

const args: Story["args"] = {
  question: "What changed before the revised proposal?",
  answer: {
    answer_text: "The account discussion preceded the customer's revised request.",
    cited_post_ids: ["post-request", "post-discussion"],
    cited_posts: [
      { post_id: "post-request", post_title: "Customer revised request" },
      { post_id: "post-discussion", post_title: "Account discussion" },
    ],
    cited_events: [
      { post_id: "post-request", post_title: "Customer revised request", observed_at: "2026-08-20T09:00:00Z", time_axis_code: "event_occurred_at" },
      { post_id: "post-discussion", post_title: "Account discussion", observed_at: "2026-08-10T09:00:00Z", time_axis_code: "created_at" },
    ],
    cited_post_evidence: [
      { post_id: "post-request", facts: [{ kind: "semantic_project", text: "project: Synthetic renewal" }] },
      { post_id: "post-discussion", facts: [{ kind: "semantic_role", text: "actor: Synthetic account owner" }] },
    ],
    source_post_ids: ["post-request", "post-discussion"],
  },
  onOpenEvidence: () => undefined,
  onOpenPost: () => undefined,
};

export const BidirectionalFocus: Story = {
  args,
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    const citation = canvas.getByRole("button", { name: "Show event 1: Customer revised request" });
    const card = canvas.getByRole("button", {
      name: "Return to answer citation 1: Customer revised request",
    });
    await userEvent.click(citation);
    await expect(card).toHaveFocus();
    await userEvent.click(card);
    await expect(citation).toHaveFocus();
  },
};

export const MissingObservedTime: Story = {
  args: {
    ...args,
    answer: {
      ...args.answer,
      cited_posts: [args.answer.cited_posts![0]],
      cited_events: [{ ...args.answer.cited_events![0], observed_at: null, time_axis_code: null }],
    },
  },
  play: async ({ canvasElement }) => {
    await expect(within(canvasElement).getByText("Observed time unavailable")).toBeVisible();
  },
};

export const NarrowViewport: Story = {
  ...BidirectionalFocus,
  parameters: { viewport: { defaultViewport: "mobile1" } },
};
