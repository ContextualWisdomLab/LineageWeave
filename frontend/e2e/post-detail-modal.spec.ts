import { test, expect } from "./fixtures";

/**
 * Authenticated-browser evidence for the post-detail modal's dialog
 * semantics (docs/product-technical-gap-baseline.md: "modal 50% mask and
 * keyboard semantics" -- source + unit already exist, this closes the
 * "authenticated browser evidence open" gap). Discovers a real post
 * through the running app's own board list rather than a fixed id
 * (AGENTS.md's synthetic-only-artifact rule) -- runs against the live
 * authenticated stack (`make up && make seed`, or an authorized real
 * import).
 */

test("post detail modal exposes dialog semantics, traps focus, and restores it on Escape", async ({ page }) => {
  await page.goto("/");

  const trigger = page.locator("button.post-list-item").first();
  await expect(trigger).toBeVisible({ timeout: 15000 });
  const triggerLabel = await trigger.getAttribute("aria-label");
  await trigger.focus();
  await trigger.click();

  const dialog = page.locator(".popup-panel");
  await expect(dialog).toBeVisible({ timeout: 15000 });
  await expect(dialog).toHaveAttribute("role", "dialog");
  await expect(dialog).toHaveAttribute("aria-modal", "true");

  // Focus moves into the panel on open, not left on the trigger button
  // behind the now-open backdrop.
  await expect(dialog).toBeFocused({ timeout: 5000 });

  // Tab cycling stays within the panel: repeatedly tabbing forward never
  // lands on an element outside .popup-panel (the backdrop's own board
  // content must not be reachable while the dialog is open).
  const focusableCount = await dialog.locator(
    'a[href], area[href], button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), summary, [tabindex]:not([tabindex="-1"])',
  ).count();
  expect(focusableCount).toBeGreaterThan(0);
  for (let step = 0; step < focusableCount + 2; step += 1) {
    await page.keyboard.press("Tab");
    const activeInsideDialog = await page.evaluate(() => {
      const panel = document.querySelector(".popup-panel");
      return panel ? panel.contains(document.activeElement) : false;
    });
    expect(activeInsideDialog).toBe(true);
  }

  // Escape closes the dialog and restores focus to the element that
  // opened it.
  await page.keyboard.press("Escape");
  await expect(dialog).not.toBeVisible({ timeout: 5000 });
  const restoredLabel = await page.evaluate(() => document.activeElement?.getAttribute("aria-label"));
  expect(restoredLabel).toBe(triggerLabel);
});
