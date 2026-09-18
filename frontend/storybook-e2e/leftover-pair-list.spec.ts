import { expect, test, type Page } from "@playwright/test";

const closestName = /^Closest leftover: Public post · sales-lead /;
const farthestName = /^Farthest leftover: Specification revision requested · negative /;

async function openStory(page: Page, storyId: string) {
  await page.goto(`/iframe.html?id=${storyId}&viewMode=story`);
  await expect(page.locator("#storybook-root")).toBeVisible();
}

test("leftover-pair actions expose the visible label and persisted evidence to browser accessibility APIs", async ({
  page,
}) => {
  await openStory(page, "reports-leftoverpairlist--closest-and-farthest");

  const closest = page.getByRole("button", { name: closestName });
  const farthest = page.getByRole("button", { name: farthestName });

  await expect(closest).toHaveAccessibleName(/R \+0\.40/);
  await expect(closest).toHaveAccessibleName(/Y 2\.40 · E 2\.00/);
  await expect(closest).toHaveAccessibleName(/d 0\.12/);
  await expect(farthest).toHaveAccessibleName(/R −1\.10/);
  await expect(farthest).toHaveAccessibleName(/d 2\.00/);

  await page.evaluate(() => (document.activeElement as HTMLElement | null)?.blur());
  await page.keyboard.press("Tab");
  await expect(closest).toBeFocused();
  await page.keyboard.press("Enter");
  await expect(closest).toBeFocused();
  await page.keyboard.press("Tab");
  await expect(farthest).toBeFocused();
});

test("dense mobile actions retain touch targets and native mouse/touch pointer delivery", async ({ page }) => {
  await page.setViewportSize({ width: 320, height: 568 });
  await openStory(page, "reports-leftoverpairlist--narrow-dense-evidence");

  const closest = page.getByRole("button", { name: closestName });
  const farthest = page.getByRole("button", { name: farthestName });

  for (const action of [closest, farthest]) {
    const box = await action.boundingBox();
    expect(box).not.toBeNull();
    expect(box!.height).toBeGreaterThanOrEqual(44);
    expect(box!.width).toBeLessThanOrEqual(320);
    const overflow = await action.evaluate((element) => element.scrollWidth - element.clientWidth);
    expect(overflow).toBeLessThanOrEqual(0);
  }

  await farthest.evaluate((element) => {
    element.addEventListener(
      "pointerdown",
      (event) => element.setAttribute("data-pointer-type", (event as PointerEvent).pointerType),
      { once: true },
    );
    element.addEventListener("click", () => element.setAttribute("data-browser-click", "true"), {
      once: true,
    });
  });
  const farthestBox = (await farthest.boundingBox())!;
  await page.mouse.click(
    farthestBox.x + farthestBox.width / 2,
    farthestBox.y + farthestBox.height / 2,
  );
  await expect(farthest).toHaveAttribute("data-pointer-type", "mouse");
  await expect(farthest).toHaveAttribute("data-browser-click", "true");

  await closest.evaluate((element) => {
    element.addEventListener(
      "pointerdown",
      (event) => element.setAttribute("data-pointer-type", (event as PointerEvent).pointerType),
      { once: true },
    );
    element.addEventListener("click", () => element.setAttribute("data-browser-click", "true"), {
      once: true,
    });
  });
  const closestBox = (await closest.boundingBox())!;
  await page.touchscreen.tap(
    closestBox.x + closestBox.width / 2,
    closestBox.y + closestBox.height / 2,
  );
  await expect(closest).toHaveAttribute("data-pointer-type", "touch");
  await expect(closest).toHaveAttribute("data-browser-click", "true");
});
