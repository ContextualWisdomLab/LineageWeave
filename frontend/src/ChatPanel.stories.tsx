import type { Meta, StoryObj } from "@storybook/react-vite";
import { ChatPanel } from "./App";

type Fixture = "empty" | "saved";

function jsonResponse(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

function installFixture(fixture: Fixture) {
  globalThis.fetch = async (input) => {
    const url = typeof input === "string" ? input : input.url;
    if (url.endsWith("/api/posts/post-1/chat/conversations/conversation-post-1")) {
      return jsonResponse({
        conversation_id: "conversation-post-1",
        title: "Saved post question",
        older_cursor: null,
        exchanges: [
          {
            turn_id: "turn-1",
            question_text: "Which site visit was saved?",
            answer_text: "The saved post answer stays grounded in the linked source.",
            cited_post_ids: ["post-2"],
            cited_posts: [{ post_id: "post-2", post_title: "Linked source post" }],
            source_post_ids: ["post-1", "post-2"],
          },
        ],
      });
    }
    if (url.includes("/chat/conversations")) {
      return jsonResponse({
        conversations:
          fixture === "saved"
            ? [
                {
                  conversation_id: "conversation-post-1",
                  title: "Saved post question",
                  updated_at: "2026-08-21T00:00:00Z",
                  turn_count: 1,
                },
              ]
            : [],
      });
    }
    return jsonResponse({
      post_id: "post-1",
      exchanges: [
        {
          question_text: "What happened between these events?",
          answer_text: "The seeded follow-up after the site visit.",
          cited_post_ids: ["post-2"],
          cited_posts: [{ post_id: "post-2", post_title: "Linked source post" }],
        },
      ],
    });
  };
}

const meta = {
  title: "Workspace/ChatPanel",
  component: ChatPanel,
  args: {
    postId: "post-1",
    accessToken: "synthetic-story-token",
  },
  parameters: { layout: "padded" },
} satisfies Meta<typeof ChatPanel>;

export default meta;
type Story = StoryObj<typeof meta>;

export const SeededDump: Story = {
  render(args) {
    installFixture("empty");
    return <ChatPanel {...args} />;
  },
};

export const SavedHistory: Story = {
  render(args) {
    installFixture("saved");
    return <ChatPanel {...args} />;
  },
};

export const Phone: Story = {
  ...SavedHistory,
  parameters: {
    layout: "padded",
    viewport: { defaultViewport: "mobile1" },
  },
};
