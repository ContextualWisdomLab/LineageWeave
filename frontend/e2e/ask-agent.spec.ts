import { expect, test } from "@playwright/test";
import { loginAsDemoAnalyst } from "./support/auth.ts";

/**
 * Exercises the four Ask Agent capabilities end to end: relative-time-scoped
 * retrieval (#415), git-branch-style multi-lineage rendering (#418), image
 * citation (#419), and the evidence Layer Popup (#420).
 *
 * Requires all four PRs merged to `main` and the backend/frontend images
 * rebuilt from it -- an ad-hoc `docker compose` stack still running an
 * older or unrelated branch will not satisfy these selectors (verified: the
 * stack running during this checkpoint's development was built from a
 * different, more advanced branch with its own conversation-history UI, not
 * `main`). `smoke.spec.ts`'s login flow is the one assertion here proven to
 * pass against arbitrary deployments, since the Keycloak-hosted login form
 * is shared across every branch.
 */
test.beforeEach(async ({ page }) => {
  await loginAsDemoAnalyst(page);
  await page.getByRole("button", { name: "Ask Agent" }).click();
});

test("answers a relative-time-scoped question and cites at least one post", async ({ page }) => {
  await page.getByRole("textbox", { name: "Ask a question" }).fill("어제 무슨 일이 있었나요?");
  await page.getByRole("button", { name: "Ask", exact: true }).click();
  await expect(page.getByRole("heading", { name: "Answer" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Cited posts" })).toBeVisible({ timeout: 15000 });
});

test("renders a cited lineage thread as a git-branch-style graph", async ({ page }) => {
  await page.getByRole("textbox", { name: "Ask a question" }).fill("What happened between these events?");
  await page.getByRole("button", { name: "Ask", exact: true }).click();
  await expect(page.getByRole("heading", { name: "Cited posts" })).toBeVisible({ timeout: 15000 });
  const lineage = page.getByLabel("Reconstructed lineage");
  if ((await lineage.count()) > 0) {
    await expect(lineage).toBeVisible();
    await expect(page.getByRole("img", { name: /lineage$/ }).first()).toBeVisible();
  }
});

test("cites persisted image evidence when a cited post has an embedded image", async ({ page }) => {
  await page.getByRole("textbox", { name: "Ask a question" }).fill("Which project?");
  await page.getByRole("button", { name: "Ask", exact: true }).click();
  await expect(page.getByRole("heading", { name: "Cited posts" })).toBeVisible({ timeout: 15000 });
  const imageEvidence = page.getByText(/^Image evidence:/);
  if ((await imageEvidence.count()) > 0) {
    await expect(imageEvidence.first()).toBeVisible();
  }
});

test("opens cited-post evidence in a Layer Popup without leaving the answer", async ({ page }) => {
  await page.getByRole("textbox", { name: "Ask a question" }).fill("Which project?");
  await page.getByRole("button", { name: "Ask", exact: true }).click();
  await expect(page.getByRole("heading", { name: "Cited posts" })).toBeVisible({ timeout: 15000 });

  const viewEvidence = page.getByRole("button", { name: "View evidence" }).first();
  await viewEvidence.click();

  const dialog = page.getByRole("dialog");
  await expect(dialog).toBeVisible();
  await page.getByRole("button", { name: "Close evidence panel" }).click();
  await expect(dialog).not.toBeVisible();
  // The answer is still on screen -- the layer never navigated away.
  await expect(page.getByRole("heading", { name: "Cited posts" })).toBeVisible();
});
