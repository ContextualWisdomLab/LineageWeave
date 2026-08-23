import { test, expect } from "./fixtures";

/**
 * Authenticated-browser evidence for SiteMapUtility (docs/product-technical-
 * gap-baseline.md: "Site map / utility menu" -- source + unit already exist,
 * this closes the "authenticated browser evidence open" gap): accessible
 * toggle/region, Escape close, and destination-close behavior.
 */

test("site map toggle exposes an accessible region and closes on Escape", async ({ page }) => {
  await page.goto("/");

  const toggle = page.getByRole("button", { name: /site map/i });
  await expect(toggle).toBeVisible({ timeout: 15000 });
  await expect(toggle).toHaveAttribute("aria-expanded", "false");
  await expect(toggle).toHaveAttribute("aria-haspopup", "true");

  await toggle.click();
  await expect(toggle).toHaveAttribute("aria-expanded", "true");
  const menu = page.locator("#site-map-menu");
  await expect(menu).toBeVisible();
  await expect(menu).toHaveAttribute("role", "region");
  await expect(page.locator("#site-map-navigation")).toBeVisible();

  await page.keyboard.press("Escape");
  await expect(menu).not.toBeVisible({ timeout: 5000 });
  await expect(toggle).toHaveAttribute("aria-expanded", "false");
});

test("selecting a destination from the site map closes it", async ({ page }) => {
  await page.goto("/");

  const toggle = page.getByRole("button", { name: /site map/i });
  await expect(toggle).toBeVisible({ timeout: 15000 });
  await toggle.click();

  const menu = page.locator("#site-map-menu");
  await expect(menu).toBeVisible();

  // Board is the default destination, so select a distinct, always-present
  // destination to prove the site-map action changes application state.
  await menu.getByRole("button", { name: "Calendar", exact: true }).click();

  await expect(menu).not.toBeVisible({ timeout: 5000 });
  await expect(toggle).toHaveAttribute("aria-expanded", "false");

  await expect(page).toHaveURL(/(?:\?|&)workspace=calendar(?:&|$)/);
  const headerNav = page.locator("nav.workspace-gnb").first();
  await expect(headerNav.getByRole("button", { name: "Calendar", exact: true })).toHaveAttribute(
    "aria-current",
    "page",
  );
  await expect(page.getByRole("main").getByRole("heading", { name: "Calendar", exact: true })).toBeVisible();
});
