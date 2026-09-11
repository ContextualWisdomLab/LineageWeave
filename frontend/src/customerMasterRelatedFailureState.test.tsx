import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, expect, it, vi } from "vitest";
import App from "./App";
import { fetchRelatedEntity } from "./api";
import { CUSTOMER_MASTER_TRANSLATION_KEYS } from "./i18n";

const RELATED_FAILURE_COPY = "This request failed. Retry the same action.";

let mockAuth: Record<string, unknown>;

vi.mock("react-oidc-context", () => ({
  useAuth: () => mockAuth,
}));

vi.mock("./api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("./api")>();
  const { CUSTOMER_MASTER_TRANSLATION_KEYS: customerMasterKeys } = await import("./i18n");
  const translations = Object.fromEntries(customerMasterKeys.map((key) => [key, key]));
  translations["This request failed. Retry the same action."] = "This request failed. Retry the same action.";
  translations.Retry = "Retry";
  return {
    ...actual,
    fetchTenantConfig: vi.fn(async () => ({ brandName: "LineageWeave" })),
    fetchMe: vi.fn(async () => ({
      user_account_id: "acct-1",
      display_name: "Demo Analyst",
      permission_codes: ["post_read"],
      corporate_entities: [{ corporate_entity_id: "corp-a", entity_name: "Alpha Corp" }],
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
    fetchTranslationScreen: vi.fn(async (_token: string, screenKey: string, locale: string) => ({
      screen_key: screenKey,
      resource_version: 1,
      locale,
      translations,
    })),
    fetchCustomerMaster: vi.fn(async () => ({
      corporate_entities: [
        {
          corporate_entity_id: "corp-a",
          corporate_entity_code: "ALPHA",
          entity_name: "Alpha Corp",
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
});

it("requires retryable related-request failure copy in the governed Customer Master screen", () => {
  expect(CUSTOMER_MASTER_TRANSLATION_KEYS).toContain(RELATED_FAILURE_COPY);
});

it("shows a retryable error instead of successful empty evidence when a related lookup fails", async () => {
  const user = userEvent.setup();
  vi.mocked(fetchRelatedEntity)
    .mockRejectedValueOnce(new Error("related lookup unavailable"))
    .mockResolvedValueOnce({
      corporate_entity_id: "corp-a",
      entity_name: "Alpha Corp",
      related: [],
    });

  render(<App />);
  await user.click(
    await screen.findByRole("button", { name: /^(?:Customer master|고객 마스터)$/ }),
  );
  await user.click(await screen.findByRole("button", { name: /Alpha Corp/ }));

  await waitFor(() => expect(fetchRelatedEntity).toHaveBeenCalledTimes(1));
  expect(await screen.findByText(RELATED_FAILURE_COPY)).toBeInTheDocument();
  expect(screen.queryByText("No linked posts yet.")).not.toBeInTheDocument();

  await user.click(screen.getByRole("button", { name: /^Retry$/ }));
  await waitFor(() => expect(fetchRelatedEntity).toHaveBeenCalledTimes(2));
  expect(await screen.findByText("No linked posts yet.")).toBeInTheDocument();
  expect(screen.queryByText(RELATED_FAILURE_COPY)).not.toBeInTheDocument();
});