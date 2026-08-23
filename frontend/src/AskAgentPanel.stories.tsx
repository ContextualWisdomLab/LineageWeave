import type { Meta, StoryObj } from "@storybook/react-vite";
import { AskAgentPanel } from "./App";

type Fixture = "empty" | "saved" | "unavailable";

function jsonResponse(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

function installFixture(fixture: Fixture) {
  globalThis.fetch = async (input) => {
    const url = String(input);
    if (fixture === "unavailable") return jsonResponse({ detail: "Ask Agent is unavailable." }, 503);
    if (url.endsWith("/api/ask/conversations/conversation-1")) {
      return jsonResponse({
        conversation_id: "conversation-1",
        title: "Saved project question",
        older_cursor: null,
        exchanges: [{
          turn_id: "turn-1",
          question_text: "Which project was saved?",
          answer_text: "The saved answer is grounded in the linked source.",
          cited_post_ids: ["post-2"],
          cited_posts: [{ post_id: "post-2", post_title: "Linked source post" }],
          cited_post_evidence: [],
          source_post_ids: ["post-1", "post-2"],
        }],
      });
    }
    return jsonResponse({
      conversations: fixture === "saved" ? [{
        conversation_id: "conversation-1",
        title: "Saved project question",
        updated_at: "2026-08-21T00:00:00Z",
        turn_count: 1,
      }] : [],
    });
  };
}

const meta = {
  title: "Workspace/AskAgentPanel",
  component: AskAgentPanel,
  args: {
    accessToken: "synthetic-story-token",
    onOpenPost: () => undefined,
  },
  parameters: { layout: "fullscreen" },
} satisfies Meta<typeof AskAgentPanel>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Unanchored: Story = {
  render(args) {
    installFixture("empty");
    return <AskAgentPanel {...args} />;
  },
};

export const Anchored: Story = {
  args: {
    anchorPostId: "post-1",
    anchorPostTitle: "Case source post",
    onClearAnchor: () => undefined,
  },
  render(args) {
    installFixture("empty");
    return <AskAgentPanel {...args} />;
  },
};

export const SavedHistory: Story = {
  render(args) {
    installFixture("saved");
    return <AskAgentPanel {...args} />;
  },
};

export const Unavailable: Story = {
  render(args) {
    installFixture("unavailable");
    return <AskAgentPanel {...args} />;
  },
};

export const Phone: Story = {
  ...Anchored,
  parameters: {
    layout: "fullscreen",
    viewport: { defaultViewport: "mobile1" },
  },
};
