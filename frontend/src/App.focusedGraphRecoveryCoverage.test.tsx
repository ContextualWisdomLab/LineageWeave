import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import App from "./App";
import { setLocale } from "./i18n";

let mockAuth: Record<string, unknown>;

vi.mock("react-oidc-context", () => ({
  useAuth: () => mockAuth,
}));

vi.mock("./LineageDag", () => ({
  LineageDag: ({ graph }: { graph: { nodes: { label: string }[] } }) => (
    <div data-testid="focused-lineage-dag">
      {graph.nodes.map((node) => node.label).join(" | ")}
    </div>
  ),
}));

function jsonResponse(body: unknown): Response {
  return new Response(JSON.stringify(body), {
    status: 200,
    headers: { "Content-Type": "application/json" },
  });
}

function postSummary(postId: string, title: string, createdAt: string) {
  return {
    post_id: postId,
    post_title: title,
    voc_type_code: "general",
    voc_type_label: "General",
    visibility_code: "public",
    visibility_label: "Public",
    post_body_excerpt: `${title} body`,
    post_body_truncated: false,
    created_at: createdAt,
  };
}

function postDetail(postId: string, title: string, createdAt: string) {
  return {
    ...postSummary(postId, title, createdAt),
    post_body: `${title} body`,
    occupational_construct_assertions: [],
    occupational_construct_evidence_status: "complete",
  };
}

let resolveAlphaGraph: ((response: Response) => void) | null = null;
let fetchMock: ReturnType<typeof vi.fn>;

beforeEach(() => {
  setLocale("en");
  window.history.replaceState({}, "", "/");
  mockAuth = {
    isLoading: false,
    isAuthenticated: true,
    error: undefined,
    user: {
      access_token: "test-access-token",
      profile: { preferred_username: "demo.analyst" },
    },
    signinRedirect: vi.fn(),
    signoutRedirect: vi.fn(),
  };

  const alphaGraph = new Promise<Response>((resolve) => {
    resolveAlphaGraph = resolve;
  });
  const never = () => new Promise<Response>(() => undefined);

  fetchMock = vi.fn((input: RequestInfo | URL) => {
    const url = String(input);

    if (url.endsWith("/api/settings")) {
      return Promise.resolve(jsonResponse({ brandName: "LineageWeave" }));
    }
    if (url.endsWith("/api/me")) {
      return Promise.resolve(
        jsonResponse({
          user_account_id: "acct-1",
          display_name: "Demo Analyst",
          preferred_locale: "en",
          permission_codes: ["post_read"],
          corporate_entities: [],
        }),
      );
    }
    if (url.includes("/api/posts?") && !url.includes("/lineage")) {
      return Promise.resolve(
        jsonResponse({
          posts: [
            postSummary("post-b", "Beta post", "2026-01-02T00:00:00Z"),
            postSummary("post-a", "Alpha post", "2026-01-01T00:00:00Z"),
          ],
          total_count: 2,
          limit: 50,
          offset: 0,
          voc_type_options: [{ code: "general", label: "General" }],
          voice_type_catalog: [{ code: "general", label: "General" }],
          visibility_options: [{ code: "public", label: "Public" }],
        }),
      );
    }
    if (url.includes("/api/lineage?post_id=post-a")) {
      return alphaGraph;
    }
    if (url.includes("/api/lineage?post_id=post-b")) {
      return Promise.reject(new Error("synthetic current graph failure"));
    }
    if (url.endsWith("/api/posts/post-a/lineage")) {
      return Promise.resolve(jsonResponse({ post_id: "post-a", direct: [], indirect: [] }));
    }
    if (url.endsWith("/api/posts/post-b/lineage")) {
      return Promise.resolve(jsonResponse({ post_id: "post-b", direct: [], indirect: [] }));
    }
    if (url.endsWith("/api/posts/post-a")) {
      return Promise.resolve(jsonResponse(postDetail("post-a", "Alpha post", "2026-01-01T00:00:00Z")));
    }
    if (url.endsWith("/api/posts/post-b")) {
      return Promise.resolve(jsonResponse(postDetail("post-b", "Beta post", "2026-01-02T00:00:00Z")));
    }

    return never();
  });
  vi.stubGlobal("fetch", fetchMock);
});

afterEach(() => {
  vi.unstubAllGlobals();
  resolveAlphaGraph = null;
});

it("keeps a late previous graph from replacing the current failed focused graph", async () => {
  render(<App />);

  const alpha = await screen.findByRole("button", { name: "View post: Alpha post" });
  const beta = await screen.findByRole("button", { name: "View post: Beta post" });

  fireEvent.click(alpha);
  await waitFor(() =>
    expect(
      fetchMock.mock.calls.some((call) => String(call[0]).includes("/api/lineage?post_id=post-a")),
    ).toBe(true),
  );

  fireEvent.click(beta);
  expect(await screen.findByRole("heading", { name: "Beta post" })).toBeInTheDocument();
  expect(await screen.findByText("No linked posts yet.")).toBeInTheDocument();
  expect(screen.queryByTestId("focused-lineage-dag")).toBeNull();

  await act(async () => {
    resolveAlphaGraph?.(
      jsonResponse({
        nodes: [
          {
            id: "post-b",
            group: "shared-thread",
            label: "Beta post from late Alpha response",
            occurred_at: "2026-01-02T00:00:00Z",
            is_root: true,
            is_branch_point: false,
          },
          {
            id: "late-alpha-neighbor",
            group: "shared-thread",
            label: "Late Alpha neighbor",
            occurred_at: "2026-01-03T00:00:00Z",
            is_root: false,
            is_branch_point: false,
          },
        ],
        edges: [
          {
            source: "post-b",
            target: "late-alpha-neighbor",
            fused_score: 0.88,
          },
        ],
        truncated: false,
      }),
    );
    await Promise.resolve();
  });

  expect(screen.getByText("No linked posts yet.")).toBeInTheDocument();
  expect(screen.queryByTestId("focused-lineage-dag")).toBeNull();
  expect(screen.queryByText("Late Alpha neighbor")).toBeNull();
});
