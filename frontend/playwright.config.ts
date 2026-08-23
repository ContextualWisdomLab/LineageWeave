import { defineConfig } from "playwright/test";

/**
 * End-to-end tests run against the already-running docker compose stack
 * (`make seed` data, Keycloak login) rather than a Playwright-managed dev
 * server, because the flows under test span frontend + backend + Postgres
 * + Keycloak. Point E2E_BASE_URL elsewhere to target another deployment.
 */
export default defineConfig({
  testDir: "./e2e",
  timeout: 60_000,
  retries: 0,
  use: {
    baseURL: process.env.E2E_BASE_URL ?? "http://localhost:15173",
    trace: "retain-on-failure",
  },
});
