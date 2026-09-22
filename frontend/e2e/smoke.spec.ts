import { expect, test } from "@playwright/test";
import { loginAsDemoAnalyst } from "./support/auth.ts";

test("logs in with PKCE, restores the requested URL, and reaches a protected destination", async ({ page }, testInfo) => {
  const protectedResponse = page.waitForResponse((response) =>
    response.url().endsWith("/api/me") && response.request().method() === "GET"
  );
  await loginAsDemoAnalyst(page, "/?auth_return=evidence#workspace");
  await expect(page).toHaveURL(/\/?auth_return=evidence#workspace$/);
  expect((await protectedResponse).ok()).toBe(true);
  await expect(page.getByRole("button", { name: "Log out" })).toBeVisible();
  await page.screenshot({
    path: testInfo.outputPath(`authenticated-${testInfo.project.name}.png`),
    mask: [page.locator("main")],
  });
});

test("rejects a callback with unrecognized state without exposing provider details", async ({ page }, testInfo) => {
  await page.goto("/?code=synthetic-invalid-code&state=synthetic-unrecognized-state#workspace");
  await expect(page.getByRole("alert")).toHaveText(
    "Sign-in could not be completed. Start again to return to your work.",
  );
  await expect(page.getByRole("button", { name: "Start sign-in again" })).toBeVisible();
  await expect(page.locator("body")).not.toContainText(/invalid_grant|correlation|state mismatch/i);
  expect(
    await page.evaluate<boolean>(
      "document.documentElement.scrollWidth <= document.documentElement.clientWidth",
    ),
  ).toBe(true);
  await page.screenshot({
    path: testInfo.outputPath(`rejected-callback-${testInfo.project.name}.png`),
    fullPage: true,
  });
});
