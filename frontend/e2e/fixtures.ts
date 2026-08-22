import { test as base, expect } from "@playwright/test";

/**
 * Demo-only Keycloak credentials, published in docker/keycloak/realm-export.json
 * for the local dev stack -- not a secret, never a production credential.
 */
const DEMO_USERNAME = process.env.LINEAGEWEAVE_E2E_USERNAME ?? "demo.analyst";
const DEMO_PASSWORD = process.env.LINEAGEWEAVE_E2E_PASSWORD ?? "lineageweave-demo-only";

export const test = base.extend({
  page: async ({ page }, use) => {
    await page.goto("/");
    const loginButton = page.getByRole("button", { name: /login|log in/i });
    if (await loginButton.isVisible({ timeout: 5000 }).catch(() => false)) {
      await loginButton.click();
      await page.waitForURL(/realms\/lineageweave-demo/, { timeout: 15000 });
      await page.fill("#username", DEMO_USERNAME);
      await page.fill("#password", DEMO_PASSWORD);
      await page.click("#kc-login");
      await page.waitForURL((url) => !url.pathname.includes("/realms/"), { timeout: 15000 });
    }
    await page.waitForLoadState("networkidle");
    await use(page);
  },
});

export { expect };
