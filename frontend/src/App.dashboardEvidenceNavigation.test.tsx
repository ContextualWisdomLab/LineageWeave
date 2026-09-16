import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { setLocale } from "./i18n";

const apiMocks = vi.hoisted(() => ({
  fetchLineageGraph: vi.fn(),
  fetchMe: vi.fn(),
  fetchPosts: vi.fn(),
  fetchTenantConfig: vi.fn(),
}));

vi.mock("react-oidc-context", () => ({
  useAuth: () => ({
    isLoading: false,
    isAuthenticated: true,
    error: undefined,
    user: {
      access_token: "test-access-token",
      profile: { preferred_username: "demo.analyst" },
    },
    signinRedirect: vi.fn(),
    signoutRedirect: vi.fn(),
  }),
}));

vi.mock("./components/OperationsDashboard", () => ({
  OperationsDashboard: ({ onOpenPost }: { onOpenPost: (postId: string) => void }) => (
    <button type="button" onClick={() => onOpenPost("dashboard-evidence-post")}>
      Open cited dashboard evidence
    </button>
  ),
}));

vi.mock("./components/OccupationRatingProfile", () => ({
  OccupationRatingProfile: () => null,
}));

vi.mock("./api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("./api")>();
  return {
    ...actual,
    fetchLineageGraph: apiMocks.fetchLineageGraph,
    fetchMe: apiMocks.fetchMe,
    fetchPosts: apiMocks.fetchPosts,
    fetchTenantConfig: apiMocks.fetchTenantConfig,
  };
});

import App from "./App";

beforeEach(() => {
  setLocale("en");
  apiMocks.fetchLineageGraph.mockReset();
  apiMocks.fetchMe.mockReset();
  apiMocks.fetchPosts.mockReset();
  apiMocks.fetchTenantConfig.mockReset();

  apiMocks.fetchTenantConfig.mockResolvedValue({ brandName: "LineageWeave" });
  apiMocks.fetchMe.mockResolvedValue({
    user_account_id: "acct-1",
    display_name: "Demo Analyst",
    permission_codes: ["post_read"],
    corporate_entities: [],
  });
  apiMocks.fetchPosts.mockResolvedValue({
    posts: [],
    total_count: 0,
    limit: 50,
    offset: 0,
    voc_type_options: [],
    voice_type_catalog: [],
    visibility_options: [],
  });
  apiMocks.fetchLineageGraph.mockResolvedValue({ nodes: [], edges: [] });

  vi.stubGlobal(
    "fetch",
    vi.fn(async () =>
      new Response(JSON.stringify({ detail: "not needed by this navigation regression" }), {
        status: 503,
        headers: { "Content-Type": "application/json" },
      }),
    ),
  );
});

afterEach(() => {
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

it("opens the exact cited dashboard post on the board", async () => {
  render(<App />);

  await screen.findByRole("heading", { name: "Board" });
  await userEvent.click(screen.getByRole("button", { name: "Dashboard" }));
  await userEvent.click(
    await screen.findByRole("button", { name: "Open cited dashboard evidence" }),
  );

  expect(await screen.findByRole("heading", { name: "Board" })).toBeInTheDocument();
  await waitFor(() =>
    expect(apiMocks.fetchLineageGraph).toHaveBeenCalledWith(
      "test-access-token",
      "dashboard-evidence-post",
    ),
  );
});
