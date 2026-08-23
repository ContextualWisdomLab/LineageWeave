import { defineConfig, devices } from "@playwright/test";

/**
 * Runs against a live authenticated stack (`make up && make seed`).
 * Never against synthetic vitest/jsdom -- these specs exercise the real
 * browser, backend, and database together. Set LINEAGEWEAVE_BASE_URL /
 * LINEAGEWEAVE_KEYCLOAK_URL to point at a non-default deployment.
 */
export default defineConfig({
  testDir: "./e2e",
  // The default 30s budget covers the whole authenticated-page fixture
  // (goto, OIDC redirect, Keycloak form submit, callback, authenticated shell) --
  // fine on a quiet machine, but the full flow's several sequential
  // network round trips can exceed it under real load. 90s gives headroom
  // without masking a genuinely hung flow.
  timeout: 90_000,
  fullyParallel: false,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  workers: 1,
  reporter: "list",
  use: {
    baseURL: process.env.LINEAGEWEAVE_BASE_URL ?? "http://localhost:15173",
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
  },
  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"] },
    },
  ],
});
