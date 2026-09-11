import { devices, expect, test, type Page } from "@playwright/test";
import { loginAsDemoAdmin } from "./support/auth.ts";

const CROSS_SHARE = "2R̂U/R² -0.24";
const CROSS_SHARE_NAME = /2R̂U\/R² -0\.24/;
const PIXEL_7 = devices["Pixel 7"];

async function openGroupingComparison(page: Page) {
  await loginAsDemoAdmin(page);
  await page.locator(".language-switcher select").selectOption("en");
  await page.getByRole("button", { name: "게시판" }).click();

  const advancedTools = page.locator("details.advanced-review-tools");
  await expect(advancedTools).toBeVisible();
  if (!(await advancedTools.getAttribute("open"))) {
    await advancedTools.locator("summary").click();
  }

  const comparison = page.getByLabel("Grouping comparison");
  await expect(comparison).toBeVisible();
  return comparison;
}

async function expectNoHorizontalOverflow(page: Page) {
  expect(
    await page.evaluate(
      "document.documentElement.scrollWidth <= Math.ceil(window.innerWidth) + 1",
    ),
  ).toBe(true);
}

test("keeps persisted cross-share actionable in the rendered accessibility tree", async ({ page }) => {
  const comparison = await openGroupingComparison(page);
  const pair = comparison.getByRole("button", { name: CROSS_SHARE_NAME }).first();

  await expect(pair).toBeVisible();
  await expect(pair).toContainText(CROSS_SHARE);
  await expect(pair.getByText(CROSS_SHARE, { exact: true })).toHaveAttribute("aria-hidden", "true");

  // Pointer hit-testing is part of acceptance, but a trial click avoids changing
  // the report state before keyboard and responsive checks run on the same node.
  await pair.hover();
  await pair.click({ trial: true });

  await pair.focus();
  await expect(pair).toBeFocused();
  await page.keyboard.press("Shift+Tab");
  await page.keyboard.press("Tab");
  await expect(pair).toBeFocused();

  await page.setViewportSize({ width: 390, height: 844 });
  await expect(pair).toBeVisible();
  await expectNoHorizontalOverflow(page);

  // Exercise every locale the exact product head exposes. When the canonical
  // translation-ledger owner adds ES/DE/FR, this loop covers them without a
  // LineageWeave-local locale fork.
  const localeSelect = page.locator(".language-switcher select");
  const locales = await localeSelect.locator("option").evaluateAll((options) =>
    options.map((option) => option.getAttribute("value") ?? ""),
  );
  expect(locales).toEqual(expect.arrayContaining(["en", "ko", "zh", "ja", "vi"]));
  for (const locale of locales) {
    await localeSelect.selectOption(locale);
    await expect(comparison.getByRole("button", { name: CROSS_SHARE_NAME }).first()).toBeVisible();
    await expectNoHorizontalOverflow(page);
  }
});

test.describe("touch interaction", () => {
  // `defaultBrowserType` is worker-scoped, so a describe-local override must
  // apply only Pixel 7 browser-context options or Playwright aborts collection.
  test.use({
    userAgent: PIXEL_7.userAgent,
    viewport: PIXEL_7.viewport,
    deviceScaleFactor: PIXEL_7.deviceScaleFactor,
    isMobile: PIXEL_7.isMobile,
    hasTouch: PIXEL_7.hasTouch,
  });

  test("keeps the cross-share pair tappable on a phone viewport", async ({ page }) => {
    const comparison = await openGroupingComparison(page);
    const pair = comparison.getByRole("button", { name: CROSS_SHARE_NAME }).first();

    await expect(pair).toBeVisible();
    await pair.tap({ trial: true });
    await expectNoHorizontalOverflow(page);
  });
});
