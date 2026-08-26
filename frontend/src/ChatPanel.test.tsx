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
  it("replaces demo cache rows when the first saved turn starts", async () => {
    vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = input instanceof Request ? input.url : String(input);
      if (url.endsWith("/chat") && init?.method === "POST") {
        return jsonResponse({
          answer_text: "Saved answer",
          cited_post_ids: [],
          cited_posts: [],
          conversation_id: "conversation-2",
        });
      }
      if (url.endsWith("/chat/conversations")) {
        return jsonResponse({ conversations: [], next_cursor: null });
      }
      return jsonResponse({
        post_id: "post-1",
        exchanges: [{
          question_text: "Demo question",
          answer_text: "Demo answer",
          cited_post_ids: [],
          cited_posts: [],
        }],
      });
    }));

    render(<ChatPanel postId="post-1" accessToken="synthetic-token" />);

    expect(await screen.findByText("Demo answer")).toBeInTheDocument();
    await userEvent.type(screen.getByPlaceholderText("What happened between these events?"), "Save this");
    await userEvent.click(screen.getByRole("button", { name: "Ask" }));

    expect(await screen.findByText("Saved answer")).toBeInTheDocument();
    expect(screen.queryByText("Demo answer")).toBeNull();
  });

  it("reopens an owned conversation and returns to the seeded new-conversation state", async () => {
    vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL) => {
      const url = input instanceof Request ? input.url : String(input);
      if (url.endsWith("/chat/conversations/conversation-1")) {
        return jsonResponse({
          conversation_id: "conversation-1",
          title: "Saved question",
          older_cursor: "2",
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
      if (url.endsWith("/chat/conversations/conversation-1?before_turn=2")) {
        return jsonResponse({
          conversation_id: "conversation-1",
          title: "Saved question",
          older_cursor: null,
          exchanges: [{
            turn_id: "turn-0",
            question_text: "What came first?",
            answer_text: "The earlier authorized evidence.",
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
    await userEvent.click(screen.getByRole("button", { name: "Load earlier messages" }));
    expect(await screen.findByText("The earlier authorized evidence.")).toBeInTheDocument();

    await userEvent.click(screen.getByRole("button", { name: "New conversation" }));
    await waitFor(() => expect(screen.getByText("Seed answer")).toBeInTheDocument());
    expect(screen.queryByText("Only authorized saved evidence.")).toBeNull();
  });

  it("offers a next action when another history page cannot be loaded", async () => {
    vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL) => {
      const url = input instanceof Request ? input.url : String(input);
      if (url.includes("before_updated_at=")) throw new TypeError("network unavailable");
      if (url.endsWith("/chat/conversations")) {
        return jsonResponse({
          conversations: [{
            conversation_id: "conversation-1",
            title: "Saved question",
            updated_at: "2026-08-26T00:00:00Z",
            turn_count: 1,
          }],
          next_cursor: {
            updated_at: "2026-08-26T00:00:00Z",
            conversation_id: "conversation-1",
          },
        });
      }
      return jsonResponse({ post_id: "post-1", exchanges: [] });
    }));

    render(<ChatPanel postId="post-1" accessToken="synthetic-token" />);

    await userEvent.click(await screen.findByRole("button", { name: "Load more" }));
    expect(await screen.findByText(
      "Conversation history could not be loaded. Start a new conversation or try again later.",
    )).toBeInTheDocument();
  });
});
