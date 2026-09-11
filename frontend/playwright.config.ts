import { defineConfig, devices } from "@playwright/test";

/**
 * Runs against the already-running docker-compose stack (`make up`), not a
 * dev-server Playwright starts itself -- authenticated product paths need
 * Postgres, Keycloak, Valkey, backend, and frontend together. LLM/vision is a
 * separate optional Compose profile; browser contracts that do not invoke it
 * must not require provider credentials just to boot. Point
 * `LINEAGEWEAVE_E2E_BASE_URL` at a different origin if the compose port mapping
 * changes.
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
