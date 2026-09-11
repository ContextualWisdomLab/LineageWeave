import type { Page } from "@playwright/test";

/** Synthetic demo identities seeded by the local product stack; never real accounts. */
const DEMO_PASSWORD = "lineageweave-demo-only";
type DemoUsername = "demo.analyst" | "demo.admin";

/** Exercise the real Keycloak authorization-code form instead of injecting a token. */
async function loginAsDemoUser(page: Page, username: DemoUsername): Promise<void> {
  await page.goto("/");
  await page.getByRole("button", { name: "Log in" }).click();
  await page.waitForURL(/\/realms\/lineageweave-demo\/protocol\/openid-connect\/auth/);
  await page.getByLabel("Username or email").fill(username);
  await page.getByLabel("Password", { exact: true }).fill(DEMO_PASSWORD);
  await page.getByRole("button", { name: "Sign In" }).click();
  await page.waitForURL((url) => !url.pathname.includes("/realms/"));
}

/** Log in with the ABAC-narrowed synthetic analyst identity. */
export async function loginAsDemoAnalyst(page: Page): Promise<void> {
  await loginAsDemoUser(page, "demo.analyst");
}

/** Log in with the synthetic product-admin identity used by advanced report tools. */
export async function loginAsDemoAdmin(page: Page): Promise<void> {
  await loginAsDemoUser(page, "demo.admin");
}
