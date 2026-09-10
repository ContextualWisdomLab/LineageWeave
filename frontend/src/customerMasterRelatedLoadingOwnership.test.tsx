import { act, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, expect, it, vi } from "vitest";
import App from "./App";
import { fetchRelatedEntity } from "./api";

let mockAuth: Record<string, unknown>;

vi.mock("react-oidc-context", () => ({
  useAuth: () => mockAuth,
}));

vi.mock("./api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("./api")>();
  const { CUSTOMER_MASTER_TRANSLATION_KEYS } = await import("./i18n");
  return {
    ...actual,
    fetchTenantConfig: vi.fn(async () => ({ brandName: "LineageWeave" })),
    fetchMe: vi.fn(async () => ({
      user_account_id: "acct-1",
      display_name: "Demo Analyst",
      permission_codes: ["post_read"],
      corporate_entities: [
        { corporate_entity_id: "corp-a", entity_name: "Alpha Corp" },
        { corporate_entity_id: "corp-b", entity_name: "Beta Corp" },
      ],
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
      translations: Object.fromEntries(CUSTOMER_MASTER_TRANSLATION_KEYS.map((key) => [key, key])),
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
        {
          corporate_entity_id: "corp-b",
          corporate_entity_code: "BETA",
          entity_name: "Beta Corp",
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

function deferred<T>() {
  let resolve!: (value: T) => void;
  const promise = new Promise<T>((resolver) => {
    resolve = resolver;
  });
  return { promise, resolve };
}

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

it("keeps entity B loading when an older same-auth entity A lookup settles first", async () => {
  const user = userEvent.setup();
  const alpha = deferred<Awaited<ReturnType<typeof fetchRelatedEntity>>>();
  const beta = deferred<Awaited<ReturnType<typeof fetchRelatedEntity>>>();
  vi.mocked(fetchRelatedEntity).mockImplementation((_token, entityId) => {
    if (entityId === "corp-a") return alpha.promise;
    if (entityId === "corp-b") return beta.promise;
    throw new Error(`unexpected entity ${entityId}`);
  });

  render(<App />);
  await user.click(
    await screen.findByRole("button", { name: /^(?:Customer master|고객 마스터)$/ }),
  );
  await user.click(await screen.findByRole("button", { name: /Alpha Corp/ }));
  await waitFor(() => expect(fetchRelatedEntity).toHaveBeenCalledWith("test-access-token", "corp-a"));

  await user.click(await screen.findByRole("button", { name: /Beta Corp/ }));
  await waitFor(() => expect(fetchRelatedEntity).toHaveBeenCalledWith("test-access-token", "corp-b"));
  expect(screen.getByRole("status")).toHaveTextContent("Loading related posts...");

  await act(async () => {
    alpha.resolve({ corporate_entity_id: "corp-a", entity_name: "Alpha Corp", related: [] });
    await alpha.promise;
  });

  expect(screen.getByRole("status")).toHaveTextContent("Loading related posts...");

  await act(async () => {
    beta.resolve({ corporate_entity_id: "corp-b", entity_name: "Beta Corp", related: [] });
    await beta.promise;
  });

  await waitFor(() => expect(screen.queryByRole("status")).not.toBeInTheDocument());
});
