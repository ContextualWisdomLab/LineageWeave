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
  it("renders repeated saved questions as distinct turns", async () => {
    vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL) => {
      const url = input instanceof Request ? input.url : String(input);
      if (url.endsWith("/chat/conversations/conversation-1")) {
        return jsonResponse({
          conversation_id: "conversation-1",
          title: "Repeated question",
          older_cursor: null,
          exchanges: [
            {
              turn_id: "turn-1",
              question_text: "What changed?",
              answer_text: "First answer",
              cited_post_ids: ["evidence-post"],
              cited_posts: [{ post_id: "evidence-post", post_title: "Saved evidence" }],
            },
            { turn_id: "turn-2", question_text: "What changed?", answer_text: "Second answer", cited_post_ids: [] },
          ],
        });
      }
      if (url.endsWith("/api/posts/evidence-post")) {
        return jsonResponse({
          post_id: "evidence-post",
          post_title: "Saved evidence",
          post_body: "Evidence from the saved conversation.",
        });
      }
      if (url.endsWith("/chat/conversations")) {
        return jsonResponse({
          conversations: [{ conversation_id: "conversation-1", title: "Repeated question", updated_at: "2026-08-26T00:00:00Z", turn_count: 2 }],
          next_cursor: null,
        });
      }
      return jsonResponse({ post_id: "post-1", exchanges: [] });
    }));

    render(<ChatPanel postId="post-1" accessToken="synthetic-token" nameFirstAsk />);
    await userEvent.selectOptions(await screen.findByLabelText("Conversation history"), "conversation-1");

    expect(await screen.findAllByText("First answer")).toHaveLength(1);
    expect(screen.getByText("Second answer")).toBeInTheDocument();
    expect(screen.queryByLabelText("Ask seed next action")).not.toBeInTheDocument();
    expect(screen.getAllByRole("button", { name: "Ask seeded question: What changed?" })).toHaveLength(2);
    await userEvent.click(screen.getByRole("button", { name: "Open evidence: Saved evidence" }));
    expect(await screen.findByRole("complementary", { name: "Evidence" })).toHaveTextContent(
      "Evidence from the saved conversation.",
    );
  });

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

  it("replaces a deleted conversation transcript when recovery creates a new one", async () => {
    vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = input instanceof Request ? input.url : String(input);
      if (url.endsWith("/chat") && init?.method === "POST") {
        return jsonResponse({
          answer_text: "Recovered answer",
          cited_post_ids: [],
          cited_posts: [],
          conversation_id: "conversation-new",
        });
      }
      if (url.endsWith("/chat/conversations/conversation-deleted")) {
        return jsonResponse({
          conversation_id: "conversation-deleted",
          title: "Deleted conversation",
          older_cursor: null,
          exchanges: [{ turn_id: "turn-old", question_text: "Old?", answer_text: "Deleted transcript", cited_post_ids: [] }],
        });
      }
      if (url.endsWith("/chat/conversations")) {
        return jsonResponse({
          conversations: [{ conversation_id: "conversation-deleted", title: "Deleted conversation", updated_at: "2026-08-26T00:00:00Z", turn_count: 1 }],
          next_cursor: null,
        });
      }
      return jsonResponse({ post_id: "post-1", exchanges: [] });
    }));

    render(<ChatPanel postId="post-1" accessToken="synthetic-token" />);
    const history = await screen.findByLabelText("Conversation history");
    await userEvent.selectOptions(history, "conversation-deleted");
    await screen.findByText("Deleted transcript");
    await userEvent.type(screen.getByPlaceholderText("What happened between these events?"), "Recover this");
    await userEvent.click(screen.getByRole("button", { name: "Ask" }));

    expect(await screen.findByText("Recovered answer")).toBeInTheDocument();
    expect(screen.queryByText("Deleted transcript")).toBeNull();
    expect(history).toHaveValue("conversation-new");
    expect(screen.queryByRole("option", { name: /Deleted conversation/ })).toBeNull();
  });

  it("does not duplicate an answered conversation when loading another page", async () => {
    vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = input instanceof Request ? input.url : String(input);
      if (url.endsWith("/chat") && init?.method === "POST") {
        return jsonResponse({
          answer_text: "Saved answer",
          cited_post_ids: [],
          cited_posts: [],
          conversation_id: "conversation-1",
        });
      }
      if (url.includes("before_updated_at=")) {
        return jsonResponse({
          conversations: [
            { conversation_id: "conversation-1", title: "Saved question", updated_at: "2026-08-26T00:02:00Z", turn_count: 2 },
            { conversation_id: "conversation-2", title: "Older question", updated_at: "2026-08-26T00:00:00Z", turn_count: 1 },
          ],
          next_cursor: null,
        });
      }
      if (url.endsWith("/chat/conversations")) {
        return jsonResponse({
          conversations: [{ conversation_id: "conversation-1", title: "Saved question", updated_at: "2026-08-26T00:01:00Z", turn_count: 1 }],
          next_cursor: { updated_at: "2026-08-26T00:00:00Z", conversation_id: "conversation-2" },
        });
      }
      return jsonResponse({ post_id: "post-1", exchanges: [] });
    }));

    render(<ChatPanel postId="post-1" accessToken="synthetic-token" />);
    await userEvent.type(await screen.findByPlaceholderText("What happened between these events?"), "Saved question");
    await userEvent.click(screen.getByRole("button", { name: "Ask" }));
    await screen.findByText("Saved answer");
    await userEvent.click(screen.getByRole("button", { name: "Load more" }));

    await waitFor(() =>
      expect(screen.getAllByRole("option", { name: "Saved question (2)" })).toHaveLength(1),
    );
    expect(screen.getByRole("option", { name: "Older question (1)" })).toBeInTheDocument();
  });

  it("discards a paginated conversation response after moving to another post", async () => {
    let resolveOldPage!: (response: Response) => void;
    const oldPage = new Promise<Response>((resolve) => { resolveOldPage = resolve; });
    vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL) => {
      const url = input instanceof Request ? input.url : String(input);
      if (url.includes("post-1/chat/conversations?")) return oldPage;
      if (url.endsWith("post-1/chat/conversations")) {
        return jsonResponse({
          conversations: [],
          next_cursor: { updated_at: "2026-08-26T00:00:00Z", conversation_id: "conversation-old" },
        });
      }
      if (url.endsWith("post-2/chat/conversations")) {
        return jsonResponse({
          conversations: [{ conversation_id: "conversation-new", title: "Current post", updated_at: "2026-08-26T00:00:00Z", turn_count: 1 }],
          next_cursor: null,
        });
      }
      return jsonResponse({ post_id: url.includes("post-2") ? "post-2" : "post-1", exchanges: [] });
    }));

    const view = render(<ChatPanel postId="post-1" accessToken="synthetic-token" />);
    await userEvent.click(await screen.findByRole("button", { name: "Load more" }));
    view.rerender(<ChatPanel postId="post-2" accessToken="synthetic-token" />);
    expect(await screen.findByRole("option", { name: "Current post (1)" })).toBeInTheDocument();
    resolveOldPage(jsonResponse({
      conversations: [{ conversation_id: "conversation-old", title: "Previous post", updated_at: "2026-08-25T00:00:00Z", turn_count: 1 }],
      next_cursor: null,
    }));

    await waitFor(() => expect(screen.queryByRole("option", { name: "Previous post (1)" })).toBeNull());
  });

  it("discards a selected conversation response after moving to another post", async () => {
    let resolveOldConversation!: (response: Response) => void;
    vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL) => {
      const url = input instanceof Request ? input.url : String(input);
      if (url.endsWith("post-1/chat/conversations/conversation-old")) {
        return new Promise<Response>((resolve) => { resolveOldConversation = resolve; });
      }
      if (url.endsWith("post-1/chat/conversations")) {
        return jsonResponse({
          conversations: [{ conversation_id: "conversation-old", title: "Previous post", updated_at: "2026-08-25T00:00:00Z", turn_count: 1 }],
          next_cursor: null,
        });
      }
      if (url.endsWith("post-2/chat/conversations")) {
        return jsonResponse({ conversations: [], next_cursor: null });
      }
      return jsonResponse({ post_id: url.includes("post-2") ? "post-2" : "post-1", exchanges: [] });
    }));

    const view = render(<ChatPanel postId="post-1" accessToken="synthetic-token" />);
    await userEvent.selectOptions(await screen.findByLabelText("Conversation history"), "conversation-old");
    await userEvent.type(
      screen.getByPlaceholderText("What happened between these events?"),
      "Question for the previous post",
    );
    view.rerender(<ChatPanel postId="post-2" accessToken="synthetic-token" />);
    resolveOldConversation(jsonResponse({
      conversation_id: "conversation-old",
      title: "Previous post",
      older_cursor: null,
      exchanges: [{ turn_id: "turn-old", question_text: "Old?", answer_text: "Stale selected answer", cited_post_ids: [] }],
    }));

    await waitFor(() => expect(screen.queryByText("Stale selected answer")).toBeNull());
    expect(screen.getByLabelText("Conversation history")).toHaveValue("");
    expect(screen.getByPlaceholderText("What happened between these events?")).toHaveValue("");
  });

  it("discards an answer response after moving to another post", async () => {
    let resolveOldAnswer!: (response: Response) => void;
    vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = input instanceof Request ? input.url : String(input);
      if (url.endsWith("post-1/chat") && init?.method === "POST") {
        return new Promise<Response>((resolve) => { resolveOldAnswer = resolve; });
      }
      if (url.endsWith("/chat/conversations")) {
        return jsonResponse({ conversations: [], next_cursor: null });
      }
      return jsonResponse({ post_id: url.includes("post-2") ? "post-2" : "post-1", exchanges: [] });
    }));

    const view = render(<ChatPanel postId="post-1" accessToken="synthetic-token" />);
    await userEvent.type(
      await screen.findByPlaceholderText("What happened between these events?"),
      "Old post question",
    );
    await userEvent.click(screen.getByRole("button", { name: "Ask" }));
    view.rerender(<ChatPanel postId="post-2" accessToken="synthetic-token" />);
    resolveOldAnswer(jsonResponse({
      answer_text: "Stale old-post answer",
      cited_post_ids: [],
      cited_posts: [],
      conversation_id: "old-post-conversation",
    }));

    await waitFor(() => expect(screen.queryByText("Stale old-post answer")).toBeNull());
    expect(screen.getByPlaceholderText("What happened between these events?")).toHaveValue("");
    expect(screen.getByRole("button", { name: "Ask" })).toBeDisabled();
  });

  it("discards an earlier-page response after moving to another post", async () => {
    let resolveOlder!: (response: Response) => void;
    vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL) => {
      const url = input instanceof Request ? input.url : String(input);
      if (url.endsWith("post-1/chat/conversations/conversation-old?before_turn=2")) {
        return new Promise<Response>((resolve) => { resolveOlder = resolve; });
      }
      if (url.endsWith("post-1/chat/conversations/conversation-old")) {
        return jsonResponse({
          conversation_id: "conversation-old",
          title: "Previous post",
          older_cursor: "2",
          exchanges: [{ turn_id: "turn-current", question_text: "Current?", answer_text: "Current old-post answer", cited_post_ids: [] }],
        });
      }
      if (url.endsWith("post-1/chat/conversations")) {
        return jsonResponse({
          conversations: [{ conversation_id: "conversation-old", title: "Previous post", updated_at: "2026-08-25T00:00:00Z", turn_count: 2 }],
          next_cursor: null,
        });
      }
      if (url.endsWith("post-2/chat/conversations")) {
        return jsonResponse({ conversations: [], next_cursor: null });
      }
      return jsonResponse({ post_id: url.includes("post-2") ? "post-2" : "post-1", exchanges: [] });
    }));

    const view = render(<ChatPanel postId="post-1" accessToken="synthetic-token" />);
    await userEvent.selectOptions(await screen.findByLabelText("Conversation history"), "conversation-old");
    await screen.findByText("Current old-post answer");
    await userEvent.click(screen.getByRole("button", { name: "Load earlier messages" }));
    view.rerender(<ChatPanel postId="post-2" accessToken="synthetic-token" />);
    resolveOlder(jsonResponse({
      conversation_id: "conversation-old",
      title: "Previous post",
      older_cursor: null,
      exchanges: [{ turn_id: "turn-earlier", question_text: "Earlier?", answer_text: "Stale earlier-page answer", cited_post_ids: [] }],
    }));

    await waitFor(() => expect(screen.queryByText("Stale earlier-page answer")).toBeNull());
    expect(screen.queryByText("Current old-post answer")).toBeNull();
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

  it("ignores an earlier-page response after another conversation is selected", async () => {
    let resolveOlder!: (response: Response) => void;
    vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL) => {
      const url = input instanceof Request ? input.url : String(input);
      if (url.endsWith("/chat/conversations/conversation-1?before_turn=2")) {
        return new Promise<Response>((resolve) => { resolveOlder = resolve; });
      }
      if (url.endsWith("/chat/conversations/conversation-1")) {
        return jsonResponse({
          conversation_id: "conversation-1",
          title: "First conversation",
          older_cursor: "2",
          exchanges: [{ turn_id: "turn-1", question_text: "First?", answer_text: "First answer", cited_post_ids: [] }],
        });
      }
      if (url.endsWith("/chat/conversations/conversation-2")) {
        return jsonResponse({
          conversation_id: "conversation-2",
          title: "Second conversation",
          older_cursor: null,
          exchanges: [{ turn_id: "turn-2", question_text: "Second?", answer_text: "Second answer", cited_post_ids: [] }],
        });
      }
      if (url.endsWith("/chat/conversations")) {
        return jsonResponse({
          conversations: [
            { conversation_id: "conversation-1", title: "First conversation", updated_at: "2026-08-26T00:00:00Z", turn_count: 1 },
            { conversation_id: "conversation-2", title: "Second conversation", updated_at: "2026-08-26T00:01:00Z", turn_count: 1 },
          ],
          next_cursor: null,
        });
      }
      return jsonResponse({ post_id: "post-1", exchanges: [] });
    }));

    render(<ChatPanel postId="post-1" accessToken="synthetic-token" />);
    const history = await screen.findByLabelText("Conversation history");
    await userEvent.selectOptions(history, "conversation-1");
    await screen.findByText("First answer");
    await userEvent.click(screen.getByRole("button", { name: "Load earlier messages" }));
    await userEvent.selectOptions(history, "conversation-2");
    await screen.findByText("Second answer");
    resolveOlder(jsonResponse({
      conversation_id: "conversation-1",
      title: "First conversation",
      older_cursor: null,
      exchanges: [{ turn_id: "turn-0", question_text: "Earlier?", answer_text: "Stale earlier answer", cited_post_ids: [] }],
    }));

    await waitFor(() => expect(screen.queryByText("Stale earlier answer")).toBeNull());
    expect(screen.getByText("Second answer")).toBeInTheDocument();
  });

  it("does not show an error from a superseded conversation selection", async () => {
    let rejectFirst!: (reason?: unknown) => void;
    vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL) => {
      const url = input instanceof Request ? input.url : String(input);
      if (url.endsWith("/chat/conversations/conversation-1")) {
        return new Promise<Response>((_resolve, reject) => { rejectFirst = reject; });
      }
      if (url.endsWith("/chat/conversations/conversation-2")) {
        return jsonResponse({
          conversation_id: "conversation-2",
          title: "Second conversation",
          older_cursor: null,
          exchanges: [{ turn_id: "turn-2", question_text: "Second?", answer_text: "Second answer", cited_post_ids: [] }],
        });
      }
      if (url.endsWith("/chat/conversations")) {
        return jsonResponse({
          conversations: [
            { conversation_id: "conversation-1", title: "First conversation", updated_at: "2026-08-26T00:00:00Z", turn_count: 1 },
            { conversation_id: "conversation-2", title: "Second conversation", updated_at: "2026-08-26T00:01:00Z", turn_count: 1 },
          ],
          next_cursor: null,
        });
      }
      return jsonResponse({ post_id: "post-1", exchanges: [] });
    }));

    render(<ChatPanel postId="post-1" accessToken="synthetic-token" />);
    const history = await screen.findByLabelText("Conversation history");
    await userEvent.selectOptions(history, "conversation-1");
    await userEvent.selectOptions(history, "conversation-2");
    await screen.findByText("Second answer");
    rejectFirst(new TypeError("network unavailable"));

    await waitFor(() => expect(screen.queryByRole("alert")).toBeNull());
    expect(screen.getByText("Second answer")).toBeInTheDocument();
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
    await userEvent.click(screen.getByRole("button", { name: "New conversation" }));
    expect(screen.queryByText(
      "Conversation history could not be loaded. Start a new conversation or try again later.",
    )).toBeNull();
  });
});
