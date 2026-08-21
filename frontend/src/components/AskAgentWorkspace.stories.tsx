import type { Meta, StoryObj } from "@storybook/react-vite";
import type { AskAgentResponse } from "../api";
import { AskAgentWorkspaceView } from "./AskAgentWorkspace";

const answered: AskAgentResponse = {
  session_id: "storybook-session",
  answer_text:
    "The revised quotation follows the pricing review and is supported by two authorized posts.",
  cited_post_ids: ["post-2"],
  cited_posts: [{ post_id: "post-2", post_title: "Pricing review follow-up" }],
  cited_post_evidence: [
    {
      post_id: "post-2",
      facts: [
        {
          kind: "semantic_project",
          text: "project: Demonstration project | evidence: revised quotation referenced in the source body",
        },
      ],
    },
  ],
  source_post_ids: ["post-1", "post-2"],
  timeline: [
    {
      post_id: "post-1",
      post_title: "Pricing review requested",
      occurred_at: "2026-01-06T09:00:00Z",
      timeline_kind: "lineage_anchor",
    },
    {
      post_id: "post-2",
      post_title: "Pricing review follow-up",
      occurred_at: "2026-01-10T11:30:00Z",
      timeline_kind: "lineage_neighbor",
    },
  ],
};

const meta = {
  title: "Ask/AskAgentWorkspace",
  component: AskAgentWorkspaceView,
  parameters: { layout: "fullscreen" },
  args: {
    question: "",
    answer: null,
    error: null,
    asking: false,
    onQuestionChange: () => undefined,
    onSubmit: () => undefined,
    onOpenPost: () => undefined,
  },
  decorators: [
    (Story) => (
      <div style={{ maxWidth: 960, margin: "0 auto", padding: 24 }}>
        <Story />
      </div>
    ),
  ],
} satisfies Meta<typeof AskAgentWorkspaceView>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Empty: Story = {};

export const Loading: Story = {
  args: {
    question: "Which project changed after the customer review?",
    asking: true,
  },
};

export const Answered: Story = {
  args: {
    question: "Which project changed after the customer review?",
    answer: answered,
  },
};

export const Unavailable: Story = {
  args: {
    question: "Which project changed after the customer review?",
    error: "Ask Agent is temporarily unavailable. Saved evidence is still available.",
  },
};

export const PhoneAnswered: Story = {
  args: {
    question: "Which project changed after the customer review?",
    answer: answered,
  },
  decorators: [
    (Story) => (
      <div style={{ maxWidth: 390, margin: "0 auto", padding: 16 }}>
        <Story />
      </div>
    ),
  ],
};
