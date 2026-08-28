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

/** Authenticate with the acceptance token when supplied, otherwise use demo OIDC. */
export async function loginAsRuntimeReader(page: Page): Promise<void> {
  const token = process.env.LINEAGEWEAVE_ACCESS_TOKEN;
  const issuer = process.env.LINEAGEWEAVE_OIDC_ISSUER;
  const clientId = process.env.LINEAGEWEAVE_OIDC_CLIENT_ID;
  if (!token || !issuer || !clientId) {
    await loginAsDemoAnalyst(page);
    return;
  }
  await page.addInitScript(
    ({ accessToken, storageKey }) => {
      localStorage.setItem(
        storageKey,
        JSON.stringify({
          access_token: accessToken,
          token_type: "Bearer",
          expires_at: Math.floor(Date.now() / 1000) + 300,
          profile: { sub: "runtime-acceptance" },
          scope: "openid",
        }),
      );
    },
    { accessToken: token, storageKey: `oidc.user:${issuer}:${clientId}` },
  );
  await page.goto("/");
}
