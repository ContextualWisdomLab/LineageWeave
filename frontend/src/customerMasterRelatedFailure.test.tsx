import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, expect, it, vi } from "vitest";
import App from "./App";
import { BackendError, fetchRelatedEntity } from "./api";

let mockAuth: Record<string, unknown>;

vi.mock("react-oidc-context", () => ({
  useAuth: () => mockAuth,
}));

vi.mock("./api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("./api")>();
  return {
    ...actual,
    fetchTenantConfig: vi.fn(async () => ({ brandName: "LineageWeave" })),
    fetchMe: vi.fn(async () => ({
      user_account_id: "acct-1",
      display_name: "Demo Analyst",
      permission_codes: ["post_read"],
      corporate_entities: [{ corporate_entity_id: "corp-demo", entity_name: "Demo Corp" }],
      preferred_locale: "en",
    })),
    fetchPosts: vi.fn(async () => ({
      posts: [],
      total_count: 0,
      limit: 50,
      offset: 0,
      voc_type_options: [],
      voice_type_catalog: [],
      visibility_options: [],
    })),
    fetchRankings: vi.fn(async () => ({
      port: "rankweave",
      status: "unavailable",
      status_reason: "rankweave_not_available",
      rankings: [],
    })),
    fetchCustomerMaster: vi.fn(async () => ({
      corporate_entities: [
        {
          corporate_entity_id: "corp-demo",
          corporate_entity_code: "DEMO",
          entity_name: "Demo Corp",
          entity_level_code: "company",
          entity_level_label: "Company",
          parent_entity_id: null,
        },
      ],
      keymen: [],
      source_customer_hints: [],
      source_author_hints: [],
      relationship_network: [],
    })),
    fetchRelatedEntity: vi.fn(),
  };
});

beforeEach(() => {
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
  vi.mocked(fetchRelatedEntity).mockReset();
  vi.mocked(fetchRelatedEntity).mockRejectedValue(
    new BackendError("/api/corporate-entities/corp-demo/related", 503, "temporarily unavailable"),
  );
});

it("keeps a failed Customer Master relationship lookup retryable instead of presenting an empty result", async () => {
  const user = userEvent.setup();
  render(<App />);

  await user.click(
    await screen.findByRole("button", { name: /^(?:Customer master|고객 마스터)$/ }),
  );
  await user.click(await screen.findByRole("button", { name: /Demo Corp/ }));

  expect(await screen.findByRole("alert")).toHaveTextContent(
    /(?:This request failed\. Retry the same action\.|요청이 실패했습니다\. 같은 조치를 다시 시도하세요\.)/,
  );
  expect(screen.queryByText(/^(?:No linked posts yet\.|아직 연결된 게시물이 없습니다\.)$/)).not.toBeInTheDocument();

  await user.click(screen.getByRole("button", { name: /^(?:Retry|다시 시도)$/ }));
  expect(fetchRelatedEntity).toHaveBeenCalledTimes(2);
  expect(await screen.findByRole("alert")).toHaveTextContent(
    /(?:This request failed\. Retry the same action\.|요청이 실패했습니다\. 같은 조치를 다시 시도하세요\.)/,
  );
});
