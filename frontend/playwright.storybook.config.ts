import { defineConfig, devices } from "@playwright/test";

/**
 * Runs browser acceptance against the already-built static Storybook. This is
 * deliberately separate from the full-stack Playwright config: LineageDag is
 * a presentation component and its responsive/focus contract must be testable
 * without Postgres, Keycloak, Valkey, or an orchestrator.
 */
export default defineConfig({
  testDir: "./e2e-storybook",
  fullyParallel: false,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  workers: 1,
  reporter: [["list"]],
  use: {
    baseURL: "http://127.0.0.1:6006",
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
  },
  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"] },
    },
  ],
  webServer: {
    command: "python3 -m http.server 6006 --directory storybook-static --bind 127.0.0.1",
    url: "http://127.0.0.1:6006/index.html",
    reuseExistingServer: !process.env.CI,
    timeout: 120_000,
  },
});
