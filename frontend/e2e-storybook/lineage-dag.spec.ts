import { expect, test } from "@playwright/test";

const story = (id: string) => `/iframe.html?id=${id}&viewMode=story`;

async function openStory(page: import("@playwright/test").Page, id: string) {
  await page.goto(story(id));
  await expect(page.locator("#storybook-root")).toBeVisible();
}

const viewportCases = [
  { name: "desktop", width: 1280, height: 900 },
  { name: "intermediate", width: 820, height: 900 },
  { name: "mobile", width: 390, height: 844 },
] as const;

for (const viewport of viewportCases) {
  test(`keeps named and truly ungrouped lineages distinct at ${viewport.name} width`, async ({ page }) => {
    await page.setViewportSize({ width: viewport.width, height: viewport.height });
    await openStory(page, "lineage-lineagedag--named-and-truly-ungrouped");

    const figures = page.locator(".lineage-dag-group");
    await expect(figures).toHaveCount(3);
    await expect(figures.nth(0).getByRole("button", { name: "Open post: Alpha record" })).toBeVisible();
    await expect(figures.nth(1).getByRole("button", { name: "Open post: Named Ungrouped record" })).toBeVisible();
    await expect(figures.nth(2).getByRole("button", { name: "Open post: Truly ungrouped record" })).toBeVisible();
    await expect(page.getByRole("region", { name: "Ungrouped lineage viewport" })).toHaveCount(2);

    const documentOverflow = await page.evaluate(() => ({
      clientWidth: document.documentElement.clientWidth,
      scrollWidth: document.documentElement.scrollWidth,
    }));
    expect(documentOverflow.scrollWidth).toBeLessThanOrEqual(documentOverflow.clientWidth + 1);

    const beforeRemount = await figures.allTextContents();
    await page.reload();
    await expect(page.locator(".lineage-dag-group")).toHaveCount(3);
    const afterRemount = await page.locator(".lineage-dag-group").allTextContents();
    expect(afterRemount).toEqual(beforeRemount);
  });
}

test("contains mobile overflow inside the lineage viewport and exposes keyboard focus", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await openStory(page, "lineage-lineagedag--mobile-scrollable");

  const viewport = page.getByRole("region", { name: "DEMO-PROJECT lineage viewport" });
  await expect(viewport).toBeVisible();
  const dimensions = await viewport.evaluate((element) => ({
    clientWidth: element.clientWidth,
    scrollWidth: element.scrollWidth,
    overflowX: getComputedStyle(element).overflowX,
  }));
  expect(dimensions.scrollWidth).toBeGreaterThan(dimensions.clientWidth);
  expect(dimensions.overflowX).toBe("auto");

  const documentOverflow = await page.evaluate(() => ({
    clientWidth: document.documentElement.clientWidth,
    scrollWidth: document.documentElement.scrollWidth,
  }));
  expect(documentOverflow.scrollWidth).toBeLessThanOrEqual(documentOverflow.clientWidth + 1);

  await page.locator("body").click({ position: { x: 1, y: 1 } });
  await page.keyboard.press("Tab");
  await expect(viewport).toBeFocused();
  const outline = await viewport.evaluate((element) => ({
    style: getComputedStyle(element).outlineStyle,
    width: getComputedStyle(element).outlineWidth,
  }));
  expect(outline.style).not.toBe("none");
  expect(outline.width).not.toBe("0px");
});

test("operates lineage edge evidence from the keyboard", async ({ page }) => {
  await page.setViewportSize({ width: 1280, height: 900 });
  await openStory(page, "lineage-lineagedag--connection-evidence");

  const viewport = page.getByRole("region", { name: "A-100 lineage viewport" });
  const edge = page.getByRole("button", {
    name: "Open connection evidence: Initial site visit and project scope discussion to Pricing renegotiation follow-up",
  });

  await page.locator("body").click({ position: { x: 1, y: 1 } });
  await page.keyboard.press("Tab");
  await expect(viewport).toBeFocused();
  await page.keyboard.press("Tab");
  await expect(edge).toBeFocused();
  await page.keyboard.press("Enter");
  await expect(edge).toHaveAttribute("aria-pressed", "true");
  await expect(page.locator("details").first()).toHaveAttribute("open", "");
});

test("keeps parallel lineage edge evidence independently keyboard-selectable", async ({ page }) => {
  await page.setViewportSize({ width: 1280, height: 900 });
  await openStory(page, "lineage-lineagedag-parallel-edges--parallel-relationships");

  const viewport = page.getByRole("region", { name: "A-100 lineage viewport" });
  const edges = page.getByRole("button", {
    name: /Open connection evidence: Initial site visit to Pricing follow-up/,
  });
  await expect(edges).toHaveCount(2);

  const labels = await edges.evaluateAll((elements) => elements.map((element) => element.getAttribute("aria-label")));
  expect(new Set(labels).size).toBe(2);

  await page.locator("body").click({ position: { x: 1, y: 1 } });
  await page.keyboard.press("Tab");
  await expect(viewport).toBeFocused();
  await page.keyboard.press("Tab");
  await expect(edges.nth(0)).toBeFocused();
  await page.keyboard.press("Enter");

  await expect(edges.nth(0)).toHaveAttribute("aria-pressed", "true");
  await expect(edges.nth(1)).toHaveAttribute("aria-pressed", "false");
  await expect(page.locator("details[open]")).toHaveCount(1);
});
