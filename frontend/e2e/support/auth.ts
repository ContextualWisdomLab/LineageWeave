import type { Page } from "@playwright/test";

/**
 * Synthetic demo credentials seeded by `make seed` -- never a real account.
 * See `backend/tests/test_api.py`'s `_fetch_demo_analyst_token` for the
 * same login this drives through the real Keycloak realm.
 */
const DEMO_USERNAME = "demo.analyst";
const DEMO_PASSWORD = "lineageweave-demo-only";

/**
 * Logs in through the real Keycloak-hosted login form (OIDC redirect,
 * not a token injected into storage) so the e2e suite exercises the same
 * authorization-code flow a reader actually goes through.
 *
 * Next action: call this once per test before interacting with any
 * authenticated destination.
 */
export async function loginAsDemoAnalyst(page: Page): Promise<void> {
  await page.goto("/");
  await page.getByRole("button", { name: "Log in" }).click();
  await page.waitForURL(/\/realms\/lineageweave-demo\/protocol\/openid-connect\/auth/);
  await page.getByLabel("Username or email").fill(DEMO_USERNAME);
  await page.getByLabel("Password", { exact: true }).fill(DEMO_PASSWORD);
  await page.getByRole("button", { name: "Sign In" }).click();
  await page.waitForURL((url) => !url.pathname.includes("/realms/"));
}
