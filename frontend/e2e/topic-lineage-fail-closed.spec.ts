import { expect, test } from "playwright/test";

/**
 * ADR 0132 decision 5, fail-closed half: a Failed topic-lineage run
 * renders its terminal state and operator next action, and renders NO
 * topic content — no invented topic identity, no evidence/inference/
 * prediction marks, because those may only come from a real TEPP
 * envelope and a Failed run has none.
 *
 * Requires the seeded compose stack (`make seed`): the seed writes a
 * Demo Corp topic-lineage run that is Failed with `tepp_not_available`
 * because no TEPP transport is connected (ADR 0022 / ADR 0132).
 */
// demo.admin: the analysis-run panel sits behind Advanced review tools,
// which requires the post_admin realm role (demo.analyst does not have it).
const DEMO_USERNAME = "demo.admin";
const DEMO_PASSWORD = "lineageweave-demo-only";
const FAILED_ROW_CAPTION = "Topic lineage · Failed · Demo Corp";

test("a Failed topic-lineage run fails closed with a named next action", async ({ page }) => {
  await page.goto("/");

  // Log in through the real Keycloak realm the compose stack ships.
  await page.getByRole("button", { name: "Log in" }).click();
  await page.locator("#username").fill(DEMO_USERNAME);
  await page.locator("#password").fill(DEMO_PASSWORD);
  await page.locator("#kc-login").click();

  // The analysis-run home is one of the Advanced review tools.
  await page.getByText("Advanced review tools").click();

  // On a deployment holding real imported source data, the synthetic
  // Demo Corp runs are hidden on purpose (ADR 0001 / ADR 0042: a reader
  // must not mistake the seeded narrative for real evidence). The
  // fail-closed walk below needs the seed-only stack `make seed` builds,
  // so skip — with the reason named — rather than fail on real data.
  const emptyState = page.getByText("No analysis runs visible to this account yet", {
    exact: false,
  });
  const failedRow = page.getByRole("button", {
    name: `Open analysis run: ${FAILED_ROW_CAPTION}`,
  });
  await expect(emptyState.or(failedRow).first()).toBeVisible();
  test.skip(
    await emptyState.isVisible(),
    "Seeded Demo Corp runs are hidden because this deployment has real source data (ADR 0001/0042); run against a make-seed-only stack.",
  );

  // Home list caption stays "kind · status · entity" (ADR 0014), and the
  // Failed row's list-level copy names the next action, not the failure code.
  await expect(failedRow).toBeVisible();
  await expect(failedRow).toContainText(
    "Open this run to see why it failed, then connect the topic-lineage service and re-run.",
  );
  await failedRow.click();

  // Detail: terminal Failed copy tells the operator to connect a
  // transport; it never promises a locally invented topic model.
  await expect(page.getByRole("heading", { name: FAILED_ROW_CAPTION })).toBeVisible();
  await expect(
    page.getByText("Connect a topic-lineage transport from this Failed row", {
      exact: false,
    }),
  ).toBeVisible();

  // The machine failure code is detail-only, on the status history (ADR 0014).
  const history = page.getByRole("list", { name: "Analysis run status history" });
  await expect(history).toContainText("tepp_not_available");

  // Fail-closed rendering: no topic-thread content and no evidence/
  // inference/prediction marks exist anywhere — a status mark without a
  // TEPP envelope would be an invented status (ADR 0132 / TEPP ADR 0016).
  await expect(page.locator(".evidence-status-mark")).toHaveCount(0);
});
