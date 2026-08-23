import { test as base, expect } from "@playwright/test";

/**
 * Demo-only Keycloak credentials, published in docker/keycloak/realm-export.json
 * for the local dev stack -- not a secret, never a production credential.
 */
const DEMO_USERNAME = process.env.LINEAGEWEAVE_E2E_USERNAME ?? "demo.analyst";
const DEMO_PASSWORD = process.env.LINEAGEWEAVE_E2E_PASSWORD ?? "lineageweave-demo-only";

export const test = base.extend({
  // oxlint's react-hooks rule pattern-matches a parameter literally named
  // "use" as React's use() hook; Playwright's fixture-injection callback
  // has no such meaning, so it is named runFixture here instead.
  page: async ({ page }, runFixture) => {
    await page.goto("/");
    const loginButton = page.getByRole("button", { name: /login|log in/i });
    if (await loginButton.isVisible({ timeout: 10000 }).catch(() => false)) {
      await loginButton.click();
      // Each step is a real network round trip (OIDC discovery, the
      // redirect to Keycloak, the form POST, the callback) -- 30s each
      // tolerates a loaded machine without masking a genuinely broken flow.
      await page.waitForURL(/realms\/lineageweave-demo/, { timeout: 30000 });
      await page.fill("#username", DEMO_USERNAME);
      await page.fill("#password", DEMO_PASSWORD);
      await page.click("#kc-login");
      await page.waitForURL((url) => !url.pathname.includes("/realms/"), { timeout: 30000 });
    }
    // "networkidle" never resolves against this app -- some background
    // connection (HMR, polling) keeps the network non-idle forever, which
    // is exactly why Playwright's own docs discourage it. Wait for the
    // authenticated shell's own navigation instead, a concrete signal the
    // initial render/data cycle is done.
    await page.getByRole("navigation").first().waitFor({ state: "visible" });
    await runFixture(page);
  },
});

export { expect };
