import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import App from "./App";

const signinRedirect = vi.fn();
const signoutRedirect = vi.fn();
let mockAuth: Record<string, unknown>;

vi.mock("react-oidc-context", () => ({
  useAuth: () => mockAuth,
}));

beforeEach(() => {
  signinRedirect.mockReset();
  signoutRedirect.mockReset();
  mockAuth = {
    isLoading: false,
    isAuthenticated: false,
    error: undefined,
    user: undefined,
    signinRedirect,
    signoutRedirect,
  };
});

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("App, unauthenticated", () => {
  it("shows a login button that starts the real OIDC redirect", async () => {
    render(<App />);
    const button = screen.getByRole("button", { name: /log in/i });
    await userEvent.click(button);
    expect(signinRedirect).toHaveBeenCalledTimes(1);
  });
});

function jsonResponse(body: unknown): Response {
  return new Response(JSON.stringify(body), { status: 200 });
}

describe("App, authenticated", () => {
  beforeEach(() => {
    mockAuth = {
      ...mockAuth,
      isAuthenticated: true,
      user: {
        access_token: "test-access-token",
        profile: { preferred_username: "demo.analyst" },
      },
    };
  });

  function stubBackend(options?: { admin?: boolean }) {
    const fetchMock = vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      const method = init?.method ?? "GET";

      if (url.endsWith("/api/me")) {
        return Promise.resolve(
          jsonResponse({
            user_account_id: options?.admin ? "acct-admin" : "acct-1",
            display_name: options?.admin ? "Demo Admin" : "Demo Analyst",
            permission_codes: options?.admin ? ["post_read", "post_admin"] : ["post_read"],
          }),
        );
      }
      if (url.endsWith("/api/lineage/rebuild") && method === "POST") {
        return Promise.resolve(jsonResponse({ edge_count: 4 }));
      }
      if (url.endsWith("/api/lineage")) {
        return Promise.resolve(
          jsonResponse({
            nodes: [
              {
                id: "post-1",
                group: "A-100",
                label: "Public post",
                occurred_at: "2026-01-01T00:00:00Z",
                is_root: true,
                is_branch_point: false,
              },
              {
                id: "post-2",
                group: "A-100",
                label: "Linked post",
                occurred_at: "2026-01-02T00:00:00Z",
                is_root: false,
                is_branch_point: false,
              },
              {
                id: "rec-002",
                group: "A-100",
                label: "Pricing renegotiation follow-up",
                occurred_at: "2026-01-06T00:00:00Z",
                is_root: false,
                is_branch_point: true,
              },
              {
                id: "rec-003",
                group: "A-100",
                label: "Pricing renegotiation: revised quote sent",
                occurred_at: "2026-01-10T00:00:00Z",
                is_root: false,
                is_branch_point: false,
              },
              {
                id: "rec-004",
                group: "A-100",
                label: "Delivery schedule question raised",
                occurred_at: "2026-01-07T00:00:00Z",
                is_root: false,
                is_branch_point: false,
              },
              {
                id: "rec-006",
                group: "A-100",
                label: "Unrelated: annual account review",
                occurred_at: "2026-02-10T00:00:00Z",
                is_root: true,
                is_branch_point: false,
              },
            ],
            edges: [
              { source: "post-1", target: "post-2", fused_score: 0.8 },
              { source: "rec-002", target: "rec-003", fused_score: 0.9 },
              { source: "rec-002", target: "rec-004", fused_score: 0.85 },
            ],
          }),
        );
      }
      if (url.endsWith("/api/posts")) {
        return Promise.resolve(
          jsonResponse([
            {
              post_id: "post-1",
              post_title: "Public post",
              voc_type_code: "voc",
              visibility_code: "public",
              created_at: "2026-01-01T00:00:00Z",
            },
          ]),
        );
      }
      if (url.endsWith("/api/posts/post-1")) {
        return Promise.resolve(
          jsonResponse({
            post_id: "post-1",
            post_title: "Public post",
            post_body: "The full body text.",
            voc_type_code: "voc",
            visibility_code: "public",
            created_at: "2026-01-01T00:00:00Z",
          }),
        );
      }
      if (url.endsWith("/api/posts/post-2")) {
        return Promise.resolve(
          jsonResponse({
            post_id: "post-2",
            post_title: "Linked post",
            post_body: "The evidence panel should show exactly this text.",
            voc_type_code: "voc",
            visibility_code: "public",
            created_at: "2026-01-02T00:00:00Z",
          }),
        );
      }
      if (url.endsWith("/api/posts/post-1/summary")) {
        return Promise.resolve(
          jsonResponse({
            post_id: "post-1",
            korean_summary: "이것은 요약입니다.",
            key_events: ["첫 번째 이벤트"],
            roles_and_responsibilities: [{ person_name: "Jordan", responsibility: "일정 안내" }],
          }),
        );
      }
      if (url.endsWith("/api/posts/post-1/keymen")) {
        return Promise.resolve(jsonResponse({ keymen: [] }));
      }
      if (url.endsWith("/api/posts/post-1/counterparties")) {
        return Promise.resolve(jsonResponse({ counterparties: [] }));
      }
      if (url.endsWith("/api/posts/post-1/lineage")) {
        return Promise.resolve(
          jsonResponse({
            post_id: "post-1",
            direct: [],
            indirect: [{ post_id: "post-2", post_title: "Linked post" }],
          }),
        );
      }
      if (url.endsWith("/api/posts/post-1/chat") && method === "POST") {
        return Promise.resolve(
          jsonResponse({
            post_id: "post-1",
            answer_text: "Here is what happened, drawing on the linked post.",
            cited_post_ids: ["post-2"],
            source_post_ids: ["post-1", "post-2"],
          }),
        );
      }
      return Promise.reject(new Error(`unexpected fetch: ${method} ${url}`));
    });
    vi.stubGlobal("fetch", fetchMock);
    return fetchMock;
  }

  it("renders the A-100 fork as a git-style DAG, not a flat edge list", async () => {
    stubBackend();
    render(<App />);
    expect(await screen.findByLabelText("A-100 lineage")).toBeInTheDocument();
    expect(screen.getByLabelText("Open post: Pricing renegotiation follow-up")).toHaveClass(
      "lineage-dag-branch",
    );
    expect(screen.getByLabelText("Open post: Unrelated: annual account review")).toHaveClass(
      "lineage-dag-root",
    );
    expect(screen.queryByText("Public post → Linked post")).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /rebuild lineage/i })).not.toBeInTheDocument();
  });

  it("opens a post from a DAG node click", async () => {
    stubBackend();
    render(<App />);
    await userEvent.click(await screen.findByLabelText("Open post: Public post"));
    await waitFor(() => expect(screen.getByText("The full body text.")).toBeInTheDocument());
  });

  it("fetches and renders the post list, then opens a detail popup on click", async () => {
    const fetchMock = stubBackend();

    render(<App />);

    const listButton = await screen.findByRole("button", { name: "View post: Public post" });
    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining("/api/posts"),
      expect.objectContaining({ headers: expect.objectContaining({ Authorization: "Bearer test-access-token" }) }),
    );

    await userEvent.click(listButton);

    await waitFor(() => expect(screen.getByText("The full body text.")).toBeInTheDocument());
  });

  it("rebuilds lineage when the account has post_admin", async () => {
    const fetchMock = stubBackend({ admin: true });
    render(<App />);
    await userEvent.click(await screen.findByRole("button", { name: /rebuild lineage/i }));
    await waitFor(() =>
      expect(fetchMock).toHaveBeenCalledWith(
        expect.stringContaining("/api/lineage/rebuild"),
        expect.objectContaining({ method: "POST" }),
      ),
    );
  });

  it("renders the Korean summary, key events, R&R, and Event Lineage panels", async () => {
    stubBackend();
    render(<App />);

    await userEvent.click(await screen.findByRole("button", { name: "View post: Public post" }));

    await waitFor(() => expect(screen.getByText("이것은 요약입니다.")).toBeInTheDocument());
    expect(screen.getByText("첫 번째 이벤트")).toBeInTheDocument();
    expect(screen.getByText(/일정 안내/)).toBeInTheDocument();
    await waitFor(() => expect(screen.getByText("간접")).toBeInTheDocument());
    expect(screen.getByText("간접").closest("li")).toHaveTextContent("Linked post");
  });

  it("asks a chat question and slides in the evidence panel for a cited source on click", async () => {
    stubBackend();
    render(<App />);

    await userEvent.click(await screen.findByRole("button", { name: "View post: Public post" }));
    await waitFor(() => expect(screen.getByPlaceholderText(/what happened/i)).toBeInTheDocument());

    await userEvent.type(screen.getByPlaceholderText(/what happened/i), "What happened?");
    await userEvent.click(screen.getByRole("button", { name: /^ask$/i }));

    await waitFor(() =>
      expect(screen.getByText("Here is what happened, drawing on the linked post.")).toBeInTheDocument(),
    );

    // The evidence panel is not shown until a citation is clicked.
    expect(screen.queryByText("The evidence panel should show exactly this text.")).not.toBeInTheDocument();

    await userEvent.click(screen.getByText("post-2".slice(0, 8)));

    await waitFor(() =>
      expect(screen.getByText("The evidence panel should show exactly this text.")).toBeInTheDocument(),
    );
  });
});
