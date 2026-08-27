import type { Meta, StoryObj } from "@storybook/react-vite";
import { expect, userEvent, within } from "storybook/test";
import { ChatPanel } from "./App";

type Fixture = "empty" | "saved" | "unavailable";

function jsonResponse(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

function installFixture(fixture: Fixture) {
  globalThis.fetch = async (input, init) => {
    const url = input instanceof Request ? input.url : String(input);
    const method = input instanceof Request ? input.method : init?.method;
    if (fixture === "unavailable" && url.endsWith("/api/posts/post-1/chat") && method === "POST") {
      return jsonResponse(
        {
          detail:
            "Post chat is unavailable. Retry in a moment. If this continues, contact your workspace administrator.",
        },
        503,
      );
    }
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
    if (url.endsWith("/api/posts/post-2")) {
      return jsonResponse({
        post_id: "post-2",
        post_title: "Linked source post",
        post_body: "Evidence from the saved conversation.",
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
  args: { nameFirstAsk: true },
  render(args) {
    installFixture("saved");
    return <ChatPanel {...args} />;
  },
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    await userEvent.selectOptions(
      await canvas.findByLabelText("Conversation history"),
      "conversation-post-1",
    );
    await userEvent.click(await canvas.findByRole("button", { name: "Open evidence: Linked source post" }));
    await expect(await canvas.findByRole("complementary", { name: "Evidence" })).toHaveTextContent(
      "Evidence from the saved conversation.",
    );
  },
};

export const Phone: Story = {
  ...SavedHistory,
  parameters: {
    layout: "padded",
    viewport: { defaultViewport: "mobile1" },
  },
};

export const UnavailableWithNextAction: Story = {
  render(args) {
    installFixture("unavailable");
    return <ChatPanel {...args} />;
  },
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    await userEvent.type(canvas.getByPlaceholderText(/what happened/i), "What changed?");
    await userEvent.click(canvas.getByRole("button", { name: /^ask$/i }));
    await expect(
      await canvas.findByText(
        "Chat is temporarily unavailable. Review the saved evidence below, then retry in a moment.",
      ),
    ).toBeVisible();
  },
};
