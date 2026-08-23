import { test, expect } from "./fixtures";

/**
 * Regression guard for the 2026-08-22 Customer Master navigation bug:
 * clicking a customer's related post used to call changeDestination("board")
 * and jump the whole workspace away from Customer Master instead of showing
 * the post in place. Discovers a real customer entity with a linked post
 * through the running app's own API rather than a fixed id (AGENTS.md's
 * synthetic-only-artifact rule) -- runs against the live authenticated
 * stack (`make up && make seed`, or an authorized real import).
 */

interface RelatedNode {
  node_id: string;
  node_type_code: string;
  label?: string;
}

async function findEntityWithRelatedPost(
  request: import("@playwright/test").APIRequestContext,
  baseURL: string,
  accessToken: string,
): Promise<{ entityId: string; entityName: string } | null> {
  const master = await request.get(`${baseURL}/api/customer-master`, {
    headers: { Authorization: `Bearer ${accessToken}` },
  });
  if (!master.ok()) return null;
  const { corporate_entities: entities } = (await master.json()) as {
    corporate_entities: { corporate_entity_id: string; entity_name: string }[];
  };
  for (const entity of entities) {
    const related = await request.get(`${baseURL}/api/corporate-entities/${entity.corporate_entity_id}/related`, {
      headers: { Authorization: `Bearer ${accessToken}` },
    });
    if (!related.ok()) continue;
    const { related: nodes } = (await related.json()) as { related: RelatedNode[] };
    if (nodes.some((node) => node.node_type_code === "node_post")) {
      return { entityId: entity.corporate_entity_id, entityName: entity.entity_name };
    }
  }
  return null;
}

test("opens a customer's related post in place, never navigating away from Customer master", async ({
  page,
  request,
}) => {
  const backendBaseURL = process.env.LINEAGEWEAVE_BACKEND_URL ?? "http://localhost:18420";
  const tokenResponse = await request.post(
    `${process.env.LINEAGEWEAVE_KEYCLOAK_URL ?? "http://localhost:18080"}/realms/lineageweave-demo/protocol/openid-connect/token`,
    {
      form: {
        client_id: "lineageweave-frontend",
        grant_type: "password",
        username: process.env.LINEAGEWEAVE_E2E_USERNAME ?? "demo.analyst",
        password: process.env.LINEAGEWEAVE_E2E_PASSWORD ?? "lineageweave-demo-only",
      },
    },
  );
  test.skip(!tokenResponse.ok(), "Keycloak token endpoint unavailable in this environment");
  const { access_token: accessToken } = (await tokenResponse.json()) as { access_token: string };

  const entity = await findEntityWithRelatedPost(request, backendBaseURL, accessToken);
  test.skip(entity === null, "No customer entity with a linked post is visible in this environment");
  const { entityName } = entity!;

  await page.goto("/");
  await page.getByRole("button", { name: "Customer master" }).click();
  await expect(page.getByRole("heading", { name: "Customer master" })).toBeVisible();

  const entityButton = page.getByRole("button", { name: new RegExp(entityName.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")) });
  await entityButton.click();

  const relatedPostButton = page.getByRole("button", { name: /^Open related post:/ }).first();
  await expect(relatedPostButton).toBeVisible({ timeout: 15000 });
  await relatedPostButton.click();

  // The fix: this popup renders in place (a fixed right-docked panel),
  // it does not navigate to Board -- Customer master stays mounted and
  // its own entity for this related post is still visible underneath.
  const popup = page.locator(".popup-panel");
  await expect(popup).toBeVisible({ timeout: 15000 });
  await expect(page.getByRole("heading", { name: "Customer master" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Board", exact: true })).not.toBeVisible();

  await popup.getByRole("button", { name: /close/i }).click();
  await expect(popup).not.toBeVisible();
  await expect(page.getByRole("heading", { name: "Customer master" })).toBeVisible();
  await expect(entityButton).toBeVisible();
});
