import { defineConfig, devices } from "@playwright/test";

/**
 * Runs against the already-running docker-compose stack (`make up`), not a
 * dev-server Playwright starts itself -- the app needs Postgres, Keycloak,
 * Valkey, and the orchestrator alongside it, which `webServer` can't provide.
 * Point `LINEAGEWEAVE_E2E_BASE_URL` at a different application origin if the
 * compose port mapping changes. When Keyverse uses a different trusted issuer,
 * set `LINEAGEWEAVE_E2E_KEYVERSE_ISSUER` as well; the login helper rejects a
 * matching realm path on every other origin before entering credentials.
 */
export default defineConfig({
  testDir: "./e2e",
  fullyParallel: false,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  workers: 1,
  reporter: [["list"]],
  use: {
    baseURL: process.env.LINEAGEWEAVE_E2E_BASE_URL ?? "http://localhost:15173",
    trace: "retain-on-failure",
  },
  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"] },
    },
  ],
});
