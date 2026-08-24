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
// A live Ask answer is an asynchronous queued job whose LLM round-trip can
// take minutes under shared-gateway load; the backend's answer client
// allows a round-trip up to 570 s. Every "answer arrived" expectation gets
// a deadline just past that, not one sized to a local mock.
const ASK_ANSWER_TIMEOUT_MS = 620_000;

test.beforeEach(async ({ page }) => {
  // The per-test budget covers login + navigation too, which on a loaded
  // host right after a container rebuild has taken minutes by itself —
  // so it is the answer deadline plus generous setup slack, not a sum of
  // ideal-case steps.
  test.setTimeout(ASK_ANSWER_TIMEOUT_MS + 420_000);
  await loginAsDemoAnalyst(page);
  await page.locator(".language-switcher select").selectOption("en");
  await page.getByRole("button", { name: "Ask Agent" }).click();
});

test("answers a relative-time-scoped question and cites at least one post", async ({ page }) => {
  // The seeded posts are dated 2026-01. Compute how many months back that
  // is from the real clock so the question keeps resolving onto the seeded
  // window as time passes instead of failing every new month.
  const now = new Date();
  const monthsAgo = Math.max(1, (now.getFullYear() - 2026) * 12 + now.getMonth());
  await page.getByRole("textbox", { name: "Ask a question" }).fill(`${monthsAgo}개월 전에 무슨 일이 있었나요?`);
  await page.getByRole("button", { name: "Ask", exact: true }).click();
  await expect(page.getByRole("heading", { name: "Answer" })).toBeVisible({ timeout: ASK_ANSWER_TIMEOUT_MS });
  await expect(page.getByRole("heading", { name: "Cited posts" })).toBeVisible({ timeout: ASK_ANSWER_TIMEOUT_MS });
});

test("renders a cited lineage thread as a git-branch-style graph", async ({ page }) => {
  await page.getByRole("textbox", { name: "Ask a question" }).fill("What happened with the Westfield Power specification?");
  await page.getByRole("button", { name: "Ask", exact: true }).click();
  await expect(page.getByRole("heading", { name: "Cited posts" })).toBeVisible({ timeout: ASK_ANSWER_TIMEOUT_MS });
  const lineage = page.getByLabel("Reconstructed lineage");
  // Fail loudly (not silently skip) if the answer stops citing a
  // multi-post lineage -- the whole point of this test.
  await expect(lineage).not.toHaveCount(0);
  await expect(lineage.first()).toBeVisible();
  await expect(page.getByRole("img", { name: /lineage$/ }).first()).toBeVisible();
});

test("cites persisted image evidence when a cited post has an embedded image", async ({ page }) => {
  await page.getByRole("textbox", { name: "Ask a question" }).fill("What synthetic raster evidence was posted?");
  await page.getByRole("button", { name: "Ask", exact: true }).click();
  await expect(page.getByRole("heading", { name: "Cited posts" })).toBeVisible({ timeout: ASK_ANSWER_TIMEOUT_MS });
  const imageEvidence = page.getByText(/^Image evidence:/);
  // Fail loudly (not silently skip) if the answer stops citing image
  // evidence -- the whole point of this test.
  await expect(imageEvidence).not.toHaveCount(0);
  await expect(imageEvidence.first()).toBeVisible();
});

test("opens cited-post evidence in a Layer Popup without leaving the answer", async ({ page }) => {
  await page.getByRole("textbox", { name: "Ask a question" }).fill("Which project did Ada West discuss during the initial site visit?");
  await page.getByRole("button", { name: "Ask", exact: true }).click();
  await expect(page.getByRole("heading", { name: "Cited posts" })).toBeVisible({ timeout: ASK_ANSWER_TIMEOUT_MS });

  const viewEvidence = page.getByRole("button", { name: "View evidence" }).first();
  await viewEvidence.click();

  const dialog = page.getByRole("dialog");
  await expect(dialog).toBeVisible();
  await page.getByRole("button", { name: "Close evidence panel" }).click();
  await expect(dialog).not.toBeVisible();
  // The answer is still on screen -- the layer never navigated away.
  await expect(page.getByRole("heading", { name: "Cited posts" })).toBeVisible();
});
