import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import { ChatPanel } from "./App";
import { setLocale } from "./i18n";

function jsonResponse(body: unknown) {
  return new Response(JSON.stringify(body), {
    status: 200,
    headers: { "Content-Type": "application/json" },
  });
}

afterEach(() => {
  vi.unstubAllGlobals();
  setLocale("en");
});

describe("ChatPanel conversation history", () => {
  it("reopens an owned conversation and returns to the seeded new-conversation state", async () => {
    vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input);
      if (url.endsWith("/chat/conversations/conversation-1")) {
        return jsonResponse({
          conversation_id: "conversation-1",
          title: "Saved question",
          older_cursor: null,
          exchanges: [{
            turn_id: "turn-1",
            question_text: "What was saved?",
            answer_text: "Only authorized saved evidence.",
            cited_post_ids: [],
            cited_posts: [],
            source_post_ids: ["post-1"],
          }],
        });
      }
      if (url.endsWith("/chat/conversations")) {
        return jsonResponse({
          conversations: [{
            conversation_id: "conversation-1",
            title: "Saved question",
            updated_at: "2026-08-26T00:00:00Z",
            turn_count: 1,
          }],
          next_cursor: null,
        });
      }
      return jsonResponse({
        post_id: "post-1",
        exchanges: [{
          question_text: "Seed question",
          answer_text: "Seed answer",
          cited_post_ids: [],
          cited_posts: [],
        }],
      });
    }));

    render(<ChatPanel postId="post-1" accessToken="synthetic-token" />);

    expect(await screen.findByText("Seed answer")).toBeInTheDocument();
    await userEvent.selectOptions(
      screen.getByLabelText("Conversation history"),
      "conversation-1",
    );
    expect(await screen.findByText("Only authorized saved evidence.")).toBeInTheDocument();

    await userEvent.click(screen.getByRole("button", { name: "New conversation" }));
    await waitFor(() => expect(screen.getByText("Seed answer")).toBeInTheDocument());
    expect(screen.queryByText("Only authorized saved evidence.")).toBeNull();
  });
});
