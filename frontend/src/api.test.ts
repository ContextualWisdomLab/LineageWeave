import { afterEach, describe, expect, it, vi } from "vitest";
import {
  askAgent,
  askPostChat,
  BackendError,
  fetchAskConversation,
  fetchAskConversations,
  fetchMe,
  fetchPostChatConversation,
  fetchPostChatConversations,
  fetchPosts,
  researchPostSources,
  setPostBookmark,
  updateTenantConfig,
} from "./api";

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("backendFetch provider-error boundary", () => {
  it("does not expose provider details from server failures", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response(
          JSON.stringify({ detail: "provider secret and upstream stack trace" }),
          { status: 502, headers: { "Content-Type": "application/json" } },
        ),
      ),
    );

    await expect(fetchMe("access-token")).rejects.toMatchObject({
      status: 502,
      message: "The service could not complete this request. Try again later.",
    });
  });

  it("turns transport failures into the same safe error type", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new Error("provider secret")));

    await expect(fetchMe("access-token")).rejects.toBeInstanceOf(BackendError);
    await expect(fetchMe("access-token")).rejects.toMatchObject({
      status: 0,
      message: "The service is unreachable. Try again later.",
    });
  });

  it("uses safe copy when a server error has no string detail", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response(JSON.stringify({ message: "provider diagnostic" }), {
          status: 500,
          headers: { "Content-Type": "application/json" },
        }),
      ),
    );

    await expect(fetchMe("access-token")).rejects.toMatchObject({
      status: 500,
      message: "The service could not complete this request. Try again later.",
    });
  });

  it("keeps tenant settings on the shared error boundary", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response(JSON.stringify({ detail: "provider diagnostic" }), {
          status: 500,
          headers: { "Content-Type": "application/json" },
        }),
      ),
    );

    await expect(updateTenantConfig("access-token", {
      brandName: "Example tenant",
      systemName: "Example system",
      copyrightYear: 2026,
      copyrightHolder: "Example tenant",
    })).rejects.toMatchObject({
      status: 500,
      message: "The service could not complete this request. Try again later.",
    });
  });
});

it("normalizes the legacy post-list payload without inventing pagination", async () => {
  vi.stubGlobal(
    "fetch",
    vi.fn().mockResolvedValue(
      new Response(JSON.stringify([{ post_id: "synthetic-post" }]), {
        headers: { "Content-Type": "application/json" },
      }),
    ),
  );

  await expect(fetchPosts("access-token")).resolves.toEqual({
    posts: [{ post_id: "synthetic-post" }],
    total_count: 1,
    limit: 1,
    offset: 0,
  });
});

it("preserves conversation cursors and identifiers on both Ask boundaries", async () => {
  const fetchMock = vi.fn().mockImplementation(() =>
    Promise.resolve(new Response("{}", { headers: { "Content-Type": "application/json" } })),
  );
  vi.stubGlobal("fetch", fetchMock);
  const cursor = { updated_at: "2026-01-01T00:00:00Z", conversation_id: "conversation synthetic" };

  await askPostChat("access-token", "post-1", "Question", "post-conversation");
  await fetchPostChatConversations("access-token", "post-1", cursor);
  await fetchPostChatConversation("access-token", "post-1", "post-conversation", 2);
  await fetchAskConversations("access-token", cursor);
  await fetchAskConversation("access-token", "global-conversation", 3);
  await askAgent("access-token", "Question", "global-conversation", "post-1");

  expect(fetchMock.mock.calls.map(([input]) => String(input))).toEqual([
    expect.stringMatching(/\/api\/posts\/post-1\/chat$/),
    expect.stringContaining("/api/posts/post-1/chat/conversations?before_updated_at=2026-01-01T00%3A00%3A00Z&before_conversation_id=conversation%20synthetic"),
    expect.stringMatching(/\/api\/posts\/post-1\/chat\/conversations\/post-conversation\?before_turn=2$/),
    expect.stringContaining("/api/ask/conversations?before_updated_at=2026-01-01T00%3A00%3A00Z&before_conversation_id=conversation%20synthetic"),
    expect.stringMatching(/\/api\/ask\/conversations\/global-conversation\?before_turn=3$/),
    expect.stringMatching(/\/api\/ask$/),
  ]);
  expect(JSON.parse(String(fetchMock.mock.calls[0][1]?.body))).toEqual({
    question: "Question",
    conversation_id: "post-conversation",
  });
  expect(JSON.parse(String(fetchMock.mock.calls[5][1]?.body))).toEqual({
    question: "Question",
    conversation_id: "global-conversation",
    anchor_post_id: "post-1",
  });
});

it("preserves list filters and explicit post mutations on the shared API boundary", async () => {
  const fetchMock = vi.fn().mockImplementation(() =>
    Promise.resolve(new Response("{}", { headers: { "Content-Type": "application/json" } })),
  );
  vi.stubGlobal("fetch", fetchMock);

  await fetchPosts("access-token", 25, 50, "  project  ", ["voc"], ["parsed"], "private", "newest");
  await setPostBookmark("access-token", "post-1", true);
  await researchPostSources("access-token", "post-1");
  await fetchPosts("access-token", 25);

  expect(String(fetchMock.mock.calls[0][0])).toContain(
    "/api/posts?limit=25&offset=50&search=project&voc_type=voc&source_detail_state=parsed&visibility=private&sort=newest",
  );
  expect(fetchMock.mock.calls[1][1]).toMatchObject({
    method: "POST",
    body: JSON.stringify({ bookmarked: true }),
  });
  expect(fetchMock.mock.calls[2][1]).toMatchObject({ method: "POST" });
  expect(String(fetchMock.mock.calls[3][0])).toContain("/api/posts?limit=25&offset=0");
});
