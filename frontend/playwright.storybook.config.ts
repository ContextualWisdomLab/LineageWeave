import { defineConfig, devices } from "@playwright/test";

/** Browser acceptance for the already-built Storybook artifact. */
export default defineConfig({
  testDir: "./storybook-e2e",
  testMatch: "**/*.pw.ts",
  fullyParallel: false,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  workers: 1,
  reporter: [["list"]],
  use: {
    baseURL: "http://127.0.0.1:6006",
    trace: "retain-on-failure",
  },
  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"], hasTouch: true },
    },
  ],
  webServer: {
    command: "python3 -m http.server 6006 --directory storybook-static",
    url: "http://127.0.0.1:6006",
    reuseExistingServer: false,
    timeout: 120_000,
  },
});
