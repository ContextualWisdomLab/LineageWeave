import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import App from "./App";
import { setLocale } from "./i18n";

const signinRedirect = vi.fn();
const signoutRedirect = vi.fn();

vi.mock("react-oidc-context", () => ({
  useAuth: () => ({
    isLoading: false,
    isAuthenticated: true,
    error: undefined,
    user: {
      access_token: "post-actions-token",
      profile: { preferred_username: "demo.analyst" },
    },
    signinRedirect,
    signoutRedirect,
  }),
}));

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

type BackendOptions = {
  bookmarkGet?: Promise<boolean>;
  bookmarkSave?: Promise<boolean>;
};

function stubBackend(options: BackendOptions = {}) {
  const bookmarkGet = options.bookmarkGet ?? Promise.resolve(false);
  const bookmarkSave = options.bookmarkSave ?? Promise.resolve(true);

  const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = new URL(String(input), "https://backend.test");
    const method = init?.method ?? "GET";

    if (url.pathname === "/api/settings") {
      return jsonResponse({ brandName: "LineageWeave" });
    }
    if (url.pathname === "/api/me") {
      return jsonResponse({
        user_account_id: "acct-1",
        display_name: "Demo Analyst",
        preferred_locale: "en",
        permission_codes: ["post_read"],
        corporate_entities: [{ corporate_entity_id: "corp-demo", entity_name: "Demo Corp" }],
      });
    }
    if (url.pathname === "/api/lineage") {
      return jsonResponse({ nodes: [], edges: [], truncated: false });
    }
    if (url.pathname === "/api/posts") {
      return jsonResponse({
        posts: [
          {
            post_id: "post-1",
            post_title: "Public post",
            voc_type_code: "voc",
            voc_type_label: "Voice of Customer",
            visibility_code: "public",
            visibility_label: "Public",
            created_at: "2026-01-01T00:00:00Z",
          },
        ],
        total_count: 1,
        limit: 50,
        offset: 0,
        voc_type_options: [{ code: "voc", label: "Voice of Customer" }],
        voice_type_catalog: [{ code: "voc", label: "Voice of Customer" }],
        visibility_options: [{ code: "public", label: "Public" }],
      });
    }
    if (url.pathname === "/api/posts/post-1") {
      return jsonResponse({
        post_id: "post-1",
        post_title: "Public post",
        post_body: "Buyer-visible post body.",
        voc_type_code: "voc",
        voc_type_label: "Voice of Customer",
        visibility_code: "public",
        visibility_label: "Public",
        created_at: "2026-01-01T00:00:00Z",
      });
    }
    if (url.pathname === "/api/posts/post-1/content") {
      return jsonResponse({ status: "ready", images: [], units: [] });
    }
    if (url.pathname === "/api/posts/post-1/bookmark" && method === "GET") {
      return jsonResponse({ post_id: "post-1", bookmarked: await bookmarkGet });
    }
    if (url.pathname === "/api/posts/post-1/bookmark" && method === "POST") {
      try {
        return jsonResponse({ post_id: "post-1", bookmarked: await bookmarkSave });
      } catch {
        return jsonResponse({ detail: "bookmark unavailable" }, 503);
      }
    }

    return jsonResponse({ detail: "not needed by post-action regression" }, 503);
  });

  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

function setNavigatorProperty(name: "share" | "clipboard", value: unknown) {
  Object.defineProperty(window.navigator, name, {
    configurable: true,
    value,
  });
}

async function renderSharedPost(options: BackendOptions = {}) {
  const fetchMock = stubBackend(options);
  window.history.replaceState({}, "", "/?post=post-1");
  render(<App />);
  const shareButton = await screen.findByRole("button", { name: "Share" });
  return { fetchMock, shareButton };
}

describe("post share and bookmark actions", () => {
  let shareDescriptor: PropertyDescriptor | undefined;
  let clipboardDescriptor: PropertyDescriptor | undefined;

  beforeEach(() => {
    setLocale("en");
    signinRedirect.mockReset();
    signoutRedirect.mockReset();
    shareDescriptor = Object.getOwnPropertyDescriptor(window.navigator, "share");
    clipboardDescriptor = Object.getOwnPropertyDescriptor(window.navigator, "clipboard");
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    if (shareDescriptor) Object.defineProperty(window.navigator, "share", shareDescriptor);
    else Reflect.deleteProperty(window.navigator, "share");
    if (clipboardDescriptor) Object.defineProperty(window.navigator, "clipboard", clipboardDescriptor);
    else Reflect.deleteProperty(window.navigator, "clipboard");
    window.history.replaceState({}, "", "/");
  });

  it("uses native share with the permanent post URL", async () => {
    const share = vi.fn().mockResolvedValue(undefined);
    setNavigatorProperty("share", share);
    setNavigatorProperty("clipboard", undefined);

    const { shareButton } = await renderSharedPost();
    fireEvent.click(shareButton);

    await waitFor(() => expect(share).toHaveBeenCalledTimes(1));
    expect(share).toHaveBeenCalledWith({
      title: "Public post",
      url: expect.stringContaining("?post=post-1"),
    });
    expect(screen.queryByText("Sharing did not start. Copy the link from the browser address bar to share this post.")).toBeNull();
  });

  it("falls back to clipboard and announces the copied permanent link", async () => {
    const writeText = vi.fn().mockResolvedValue(undefined);
    setNavigatorProperty("share", undefined);
    setNavigatorProperty("clipboard", { writeText });

    const { shareButton } = await renderSharedPost();
    fireEvent.click(shareButton);

    await waitFor(() => expect(writeText).toHaveBeenCalledTimes(1));
    expect(writeText.mock.calls[0]?.[0]).toContain("?post=post-1");
    expect(await screen.findByText("Permanent link copied.")).toBeInTheDocument();
  });

  it("announces the manual fallback when no share capability is available", async () => {
    setNavigatorProperty("share", undefined);
    setNavigatorProperty("clipboard", undefined);

    const { shareButton } = await renderSharedPost();
    fireEvent.click(shareButton);

    expect(
      await screen.findByText(
        "Sharing did not start. Copy the link from the browser address bar to share this post.",
      ),
    ).toBeInTheDocument();
  });

  it("does not turn user-cancelled native share into an error", async () => {
    const share = vi.fn().mockRejectedValue(new DOMException("cancelled", "AbortError"));
    setNavigatorProperty("share", share);
    setNavigatorProperty("clipboard", undefined);

    const { shareButton } = await renderSharedPost();
    fireEvent.click(shareButton);

    await waitFor(() => expect(share).toHaveBeenCalledTimes(1));
    expect(screen.queryByText("Sharing did not start. Copy the link from the browser address bar to share this post.")).toBeNull();
  });

  it("announces a non-cancellation share failure", async () => {
    const share = vi.fn().mockRejectedValue(new Error("share failed"));
    setNavigatorProperty("share", share);
    setNavigatorProperty("clipboard", undefined);

    const { shareButton } = await renderSharedPost();
    fireEvent.click(shareButton);

    expect(
      await screen.findByText(
        "Sharing did not start. Copy the link from the browser address bar to share this post.",
      ),
    ).toBeInTheDocument();
  });

  it("keeps bookmark disabled until state is known, then persists and reflects the saved state", async () => {
    let resolveBookmark!: (value: boolean) => void;
    const bookmarkGet = new Promise<boolean>((resolve) => {
      resolveBookmark = resolve;
    });

    const { fetchMock } = await renderSharedPost({ bookmarkGet });
    const pendingButton = screen.getByRole("button", { name: "Bookmark" });
    expect(pendingButton).toBeDisabled();

    resolveBookmark(false);
    await waitFor(() => expect(pendingButton).toBeEnabled());
    fireEvent.click(pendingButton);

    const savedButton = await screen.findByRole("button", { name: "Bookmarked" });
    expect(savedButton).toHaveAttribute("aria-pressed", "true");
    const saves = fetchMock.mock.calls.filter(([input, init]) => {
      const url = new URL(String(input), "https://backend.test");
      return url.pathname === "/api/posts/post-1/bookmark" && (init?.method ?? "GET") === "POST";
    });
    expect(saves).toHaveLength(1);
    expect(JSON.parse(String(saves[0]?.[1]?.body))).toEqual({ bookmarked: true });
  });

  it("prevents duplicate bookmark saves while the first save is pending", async () => {
    let resolveSave!: (value: boolean) => void;
    const bookmarkSave = new Promise<boolean>((resolve) => {
      resolveSave = resolve;
    });

    const { fetchMock } = await renderSharedPost({ bookmarkSave });
    const button = await screen.findByRole("button", { name: "Bookmark" });
    await waitFor(() => expect(button).toBeEnabled());

    fireEvent.click(button);
    expect(button).toBeDisabled();
    fireEvent.click(button);

    const savesBeforeResolve = fetchMock.mock.calls.filter(([input, init]) => {
      const url = new URL(String(input), "https://backend.test");
      return url.pathname === "/api/posts/post-1/bookmark" && (init?.method ?? "GET") === "POST";
    });
    expect(savesBeforeResolve).toHaveLength(1);

    resolveSave(true);
    expect(await screen.findByRole("button", { name: "Bookmarked" })).toBeEnabled();
  });

  it("keeps the current bookmark state and reports a save failure", async () => {
    let rejectSave!: (error: Error) => void;
    const bookmarkSave = new Promise<boolean>((_resolve, reject) => {
      rejectSave = reject;
    });
    const { fetchMock, shareButton } = await renderSharedPost({ bookmarkSave });
    expect(shareButton).toBeEnabled();
    const button = await screen.findByRole("button", { name: "Bookmark" });
    await waitFor(() => expect(button).toBeEnabled());

    fireEvent.click(button);
    await waitFor(() => {
      const saves = fetchMock.mock.calls.filter(([input, init]) => {
        const url = new URL(String(input), "https://backend.test");
        return url.pathname === "/api/posts/post-1/bookmark" && (init?.method ?? "GET") === "POST";
      });
      expect(saves).toHaveLength(1);
    });
    rejectSave(new Error("bookmark failed"));

    expect(
      await screen.findByText(
        "Bookmark could not be saved. Try again in a moment; the post itself stays open.",
      ),
    ).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Bookmark" })).toBeEnabled();
    expect(screen.getByRole("button", { name: "Bookmark" })).toHaveAttribute("aria-pressed", "false");
  });
});
