import { expect, test } from "@playwright/test";

test("renders the authenticated operations Dashboard with grounded cases", async ({
  page,
}, testInfo) => {
  const accessToken = process.env.LINEAGEWEAVE_ACCESS_TOKEN;
  const issuer = process.env.LINEAGEWEAVE_OIDC_ISSUER;
  const clientId = process.env.LINEAGEWEAVE_OIDC_CLIENT_ID;
  const screenshotPath =
    testInfo.project.name === "chromium-mobile"
      ? process.env.SCREENSHOT_MOBILE_PATH
      : process.env.SCREENSHOT_DESKTOP_PATH;
  const requireGroundedCase = process.env.REQUIRE_GROUNDED_CASE !== "false";
  if (!accessToken || !issuer || !clientId || !screenshotPath) {
    throw new Error("runtime OIDC and screenshot environment is required");
  }

  await page.addInitScript(
    ({ token, storageKey }) => {
      const storage = (
        globalThis as unknown as { localStorage: { setItem(key: string, value: string): void } }
      ).localStorage;
      storage.setItem(
        storageKey,
        JSON.stringify({
          access_token: token,
          token_type: "Bearer",
          expires_at: Math.floor(Date.now() / 1000) + 300,
          profile: { sub: "runtime-acceptance" },
          scope: "openid",
        }),
      );
    },
    { token: accessToken, storageKey: `oidc.user:${issuer}:${clientId}` },
  );

  const dashboardResponse = page.waitForResponse((response) => {
    const url = new URL(response.url());
    return url.pathname === "/api/dashboard" && response.ok();
  });
  const voiceSummaryResponse = page.waitForResponse((response) => {
    const url = new URL(response.url());
    return url.pathname === "/api/voice-taxonomy/summary" && response.ok();
  });
  await page.goto("/");
  await Promise.all([dashboardResponse, voiceSummaryResponse]);
  const language = page.locator(".language-switcher select");
  await language.selectOption("en");
  await expect(page.locator("html")).toHaveAttribute("lang", "en");
  await expect(page.getByRole("heading", { name: "Operations evidence dashboard" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Topic model influence over time" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Voice evidence overview" })).toBeVisible();
  const navigation = page.getByRole("navigation", { name: "Workspace navigation" });
  for (const label of ["Dashboard", "External information", "Board", "Customer master", "Calendar", "Ask Agent"]) {
    await expect(navigation.getByRole("button", { name: label, exact: true })).toBeVisible();
  }
  await expect(page.getByText("운영 근거 대시보드")).toHaveCount(0);
  for (const koreanLabel of ["전체 기간 · Event 발생일", "클레임 원인 규명", "재입찰 · 인수인계", "발주 공고 · 시장 동향", "반복 이슈"]) {
    await expect(page.getByText(koreanLabel, { exact: true })).toHaveCount(0);
  }
  if (requireGroundedCase) {
    await expect(page.locator(".dashboard-case-card").first()).toBeVisible();
    const evidenceAction = page.locator(".dashboard-case-card button").first();
    await expect(evidenceAction).toBeVisible();
    await evidenceAction.click();
    const evidenceDialog = page.getByRole("dialog");
    await expect(evidenceDialog).toBeVisible();
    await evidenceDialog.getByRole("button", { name: "Close" }).click();
    await expect(evidenceDialog).not.toBeVisible();
  }
  await page.screenshot({ path: screenshotPath, fullPage: true });

  await language.selectOption("ko");
  await expect(page.locator("html")).toHaveAttribute("lang", "ko");
  await expect(page.getByRole("heading", { name: "운영 근거 대시보드" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "시간 흐름별 주제 영향도" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "글 유형 근거 현황" })).toBeVisible();
  const koreanNavigation = page.getByRole("navigation", { name: "워크스페이스 메뉴" });
  for (const label of ["대시보드", "외부 정보", "게시판", "고객 마스터", "캘린더", "에이전트에게 질문"]) {
    await expect(koreanNavigation.getByRole("button", { name: label, exact: true })).toBeVisible();
  }
  await expect(page.getByText("Operations evidence dashboard")).toHaveCount(0);
  await expect(page.getByText("전체 기간 · 사건 발생일", { exact: true })).toBeVisible();
  await expect(page.getByText("클레임 원인 규명", { exact: true }).first()).toBeVisible();
});
