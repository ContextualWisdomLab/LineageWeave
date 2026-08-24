import { expect, test } from "@playwright/test";
import { loginAsDemoAnalyst } from "./support/auth.ts";

test("logs in and reaches an authenticated destination", async ({ page }) => {
  await loginAsDemoAnalyst(page);
  await expect(page.getByRole("button", { name: "Ask Agent" })).toBeVisible();
});
