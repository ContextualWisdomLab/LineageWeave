import assert from "node:assert/strict";
import { chromium } from "playwright";

const baseUrl = process.env.LINEAGEWEAVE_E2E_LOGIN_BASE_URL || "http://127.0.0.1:18100";
const expectUnavailable = process.env.LINEAGEWEAVE_E2E_LOGIN_EXPECT_UNAVAILABLE === "1";
const browser = await chromium.launch({ headless: true });

try {
  const page = await browser.newPage({ viewport: { width: 1280, height: 960 } });
  if (expectUnavailable) {
    await page.route(/^https?:\/\//, (route) => {
      const target = new URL(route.request().url());
      return target.origin === new URL(baseUrl).origin ? route.continue() : route.abort();
    });
  }
  await page.goto(baseUrl, { waitUntil: "networkidle" });
  assert.equal(await page.getByText("글 자체의 Lineage", { exact: true }).count(), 1);
  const email = page.getByLabel("업무 이메일");
  const submit = page.getByRole("button", { name: "계속하기" });

  await submit.click();
  assert.equal(await page.locator("#emailError").textContent(), "업무 이메일을 입력해 주세요.");

  await email.fill("not-an-email");
  await submit.click();
  assert.equal(await page.locator("#emailError").textContent(), "올바른 업무 이메일 주소를 입력해 주세요.");

  const result = {
    placeholder: await email.getAttribute("placeholder"),
    unavailable: false,
  };
  if (expectUnavailable) {
    await email.fill("member@example.com");
    const response = await Promise.all([
      page.waitForResponse((item) => new URL(item.url()).pathname === "/api/login"),
      submit.click(),
    ]).then(([item]) => item);
    assert.equal(response.status(), 503);
    assert.equal(
      await page.locator("#emailError").textContent(),
      "로그인을 시작할 수 없습니다. 잠시 후 다시 시도하거나 관리자에게 문의해 주세요.",
    );
    assert.equal(page.url(), `${baseUrl.replace(/\/$/, "")}/`);
    result.unavailable = true;
  }
  const text = await page.locator("body").innerText();
  assert.equal(/\b(?:OIDC|PKCE|SSO)\b|패스키/.test(text), false);
  console.log(JSON.stringify(result));
} finally {
  await browser.close();
}
