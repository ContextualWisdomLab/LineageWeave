import type { Page } from "@playwright/test";

/**
 * Synthetic demo credentials seeded by `make seed` -- never a real account.
 * See `backend/tests/test_api.py`'s `_fetch_demo_analyst_token` for the
 * same login this drives through the real Keycloak realm.
 */
const DEMO_USERNAME = "demo.analyst";
const DEMO_PASSWORD = "lineageweave-demo-only";
const DEFAULT_KEYVERSE_ISSUER = "http://localhost:18080/realms/lineageweave-demo";
const KEYVERSE_ISSUER = process.env.LINEAGEWEAVE_E2E_KEYVERSE_ISSUER ?? DEFAULT_KEYVERSE_ISSUER;
const DEFAULT_APPLICATION_URL = "http://localhost:15173";
const APPLICATION_URL = process.env.LINEAGEWEAVE_E2E_BASE_URL ?? DEFAULT_APPLICATION_URL;

/**
 * Returns true only for the configured Keyverse issuer's authorization path.
 * Matching the realm path alone is insufficient because credentials must never
 * be entered on another origin that happens to expose the same path.
 */
export function isExpectedKeyverseAuthorizationUrl(
  url: URL,
  expectedIssuer: string = KEYVERSE_ISSUER,
): boolean {
  const issuer = new URL(expectedIssuer);
  const issuerPath = issuer.pathname.replace(/\/+$/, "");
  return (
    url.origin === issuer.origin &&
    url.pathname === `${issuerPath}/protocol/openid-connect/auth`
  );
}

/** Return whether OIDC navigation has reached the configured application origin. */
export function isExpectedApplicationUrl(
  url: URL,
  expectedApplicationUrl: string = APPLICATION_URL,
): boolean {
  return url.origin === new URL(expectedApplicationUrl).origin;
}

/**
 * Logs in through the real Keycloak-hosted login form (OIDC redirect,
 * not a token injected into storage) so the e2e suite exercises the same
 * authorization-code flow a reader actually goes through.
 *
 * Next action: call this once per test before interacting with any
 * authenticated destination.
 */
export async function loginAsDemoAnalyst(page: Page): Promise<void> {
  const isExpectedAuthorizationUrl = (url: URL) => isExpectedKeyverseAuthorizationUrl(url);

  await page.goto("/");
  await page.getByRole("button", { name: "Log in" }).click();
  try {
    await page.waitForURL(isExpectedAuthorizationUrl, {
      waitUntil: "commit",
    });
  } catch (error) {
    if (!(error instanceof Error && /ERR_ABORTED|frame was detached/.test(error.message))) {
      throw error;
    }
  }
  await page.waitForURL(isExpectedAuthorizationUrl, { waitUntil: "commit" });
  await page.getByLabel("Username or email").waitFor({ state: "visible" });
  await page.getByLabel("Username or email").fill(DEMO_USERNAME);
  await page.getByLabel("Password", { exact: true }).fill(DEMO_PASSWORD);
  await page.getByRole("button", { name: "Sign In" }).click();
  await page.waitForURL((url) => isExpectedApplicationUrl(url));
}
