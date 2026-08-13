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

  it("fetches and renders the post list, then opens a detail popup on click", async () => {
    const fetchMock = vi.fn((input: RequestInfo | URL) => {
      const url = String(input);
      if (url.endsWith("/api/posts")) {
        return Promise.resolve(
          new Response(
            JSON.stringify([
              {
                post_id: "post-1",
                post_title: "Public post",
                voc_type_code: "voc",
                visibility_code: "public",
                created_at: "2026-01-01T00:00:00Z",
              },
            ]),
            { status: 200 },
          ),
        );
      }
      if (url.endsWith("/api/posts/post-1")) {
        return Promise.resolve(
          new Response(
            JSON.stringify({
              post_id: "post-1",
              post_title: "Public post",
              post_body: "The full body text.",
              voc_type_code: "voc",
              visibility_code: "public",
              created_at: "2026-01-01T00:00:00Z",
            }),
            { status: 200 },
          ),
        );
      }
      return Promise.reject(new Error(`unexpected fetch: ${url}`));
    });
    vi.stubGlobal("fetch", fetchMock);

    render(<App />);

    await screen.findByText("Public post");
    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining("/api/posts"),
      expect.objectContaining({ headers: { Authorization: "Bearer test-access-token" } }),
    );

    await userEvent.click(screen.getByText("Public post"));

    await waitFor(() => expect(screen.getByText("The full body text.")).toBeInTheDocument());
  });
});
