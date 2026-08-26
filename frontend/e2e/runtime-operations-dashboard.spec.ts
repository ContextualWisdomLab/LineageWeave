import { expect, test } from "@playwright/test";

test("renders the authenticated operations Dashboard with grounded cases", async ({
  page,
}, testInfo) => {
  const accessToken = process.env.LINEAGEWEAVE_ACCESS_TOKEN;
  const issuer = process.env.LINEAGEWEAVE_OIDC_ISSUER;
  const clientId = process.env.LINEAGEWEAVE_OIDC_CLIENT_ID;
  const screenshotPath =
    testInfo.project.name === "chromium-mobile"
      ? process.env.SCREENSHOT_MOBILE_PATH
      : process.env.SCREENSHOT_DESKTOP_PATH;
  const requireGroundedCase = process.env.REQUIRE_GROUNDED_CASE !== "false";
  if (!accessToken || !issuer || !clientId || !screenshotPath) {
    throw new Error("runtime OIDC and screenshot environment is required");
  }

  await page.addInitScript(
    ({ token, storageKey }) => {
      const storage = (
        globalThis as unknown as { localStorage: { setItem(key: string, value: string): void } }
      ).localStorage;
      storage.setItem(
        storageKey,
        JSON.stringify({
          access_token: token,
          token_type: "Bearer",
          expires_at: Math.floor(Date.now() / 1000) + 300,
          profile: { sub: "runtime-acceptance" },
          scope: "openid",
        }),
      );
    },
    { token: accessToken, storageKey: `oidc.user:${issuer}:${clientId}` },
  );

  await page.goto("/");
  await expect(page.getByRole("heading", { name: "운영 근거 Dashboard" })).toBeVisible();
  if (requireGroundedCase) {
    await expect(page.locator(".dashboard-case-card").first()).toBeVisible();
  }
  await page.screenshot({ path: screenshotPath, fullPage: true });
});
