import { expect, test } from "@playwright/test";

function jwtExpiry(accessToken: string): number {
  const segments = accessToken.split(".");
  if (segments.length !== 3) throw new Error("runtime access token must be a JWT");
  const payload = JSON.parse(Buffer.from(segments[1], "base64url").toString("utf8")) as {
    exp?: unknown;
  };
  if (!Number.isInteger(payload.exp)) throw new Error("runtime access token must carry exp");
  return payload.exp as number;
}

test("asks one operator-supplied question and opens cited evidence", async ({ page }, testInfo) => {
  const accessToken = process.env.LINEAGEWEAVE_ACCESS_TOKEN;
  const issuer = process.env.LINEAGEWEAVE_OIDC_ISSUER;
  const clientId = process.env.LINEAGEWEAVE_OIDC_CLIENT_ID;
  const question = process.env.LINEAGEWEAVE_RUNTIME_ASK_QUESTION?.trim();
  const timeoutSeconds = Number(process.env.LINEAGEWEAVE_RUNTIME_ASK_TIMEOUT_SECONDS);
  const screenshotPath =
    testInfo.project.name === "chromium-mobile"
      ? process.env.ASK_SCREENSHOT_MOBILE_PATH
      : process.env.ASK_SCREENSHOT_DESKTOP_PATH;
  if (
    !accessToken ||
    !issuer ||
    !clientId ||
    !question ||
    !screenshotPath ||
    !Number.isInteger(timeoutSeconds) ||
    timeoutSeconds <= 0
  ) {
    throw new Error("runtime Ask token, OIDC, question, timeout, and screenshot environment is required");
  }
  test.setTimeout(timeoutSeconds * 1000);
  if (jwtExpiry(accessToken) - Math.floor(Date.now() / 1000) < timeoutSeconds) {
    throw new Error("runtime Ask access token expires before the declared observation budget");
  }

  await page.addInitScript(
    ({ token, storageKey, expiresAt }) => {
      localStorage.setItem(
        storageKey,
        JSON.stringify({
          access_token: token,
          token_type: "Bearer",
          expires_at: expiresAt,
          profile: { sub: "runtime-acceptance" },
          scope: "openid",
        }),
      );
    },
    { token: accessToken, storageKey: `oidc.user:${issuer}:${clientId}`, expiresAt: jwtExpiry(accessToken) },
  );
  await page.goto("/");
  await page.locator(".language-switcher select").selectOption("en");
  await page.getByRole("button", { name: "Ask Agent" }).click();
  await page.getByRole("textbox", { name: "Ask a question" }).fill(question);
  await page.getByRole("button", { name: "Ask", exact: true }).click();
  await expect(page.getByRole("heading", { name: "Answer" })).toBeVisible({
    timeout: timeoutSeconds * 1000,
  });
  await expect(page.getByRole("heading", { name: "Cited posts" })).toBeVisible();
  await page.screenshot({ path: screenshotPath, fullPage: true });

  await page.getByRole("button", { name: "View evidence" }).first().click();
  const dialog = page.getByRole("dialog");
  await expect(dialog).toBeVisible();
  await dialog.getByRole("button", { name: "Close evidence panel" }).click();
  await expect(dialog).not.toBeVisible();
  await expect(page.getByRole("heading", { name: "Cited posts" })).toBeVisible();
});
