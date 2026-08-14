import { chromium } from 'playwright';

const loginBase = 'http://127.0.0.1:18082';
const browser = await chromium.launch({ headless: true });
const context = await browser.newContext();
const page = await context.newPage();

try {
  await page.goto(loginBase);
  await page.locator('#loginBtn').click();
  await page.waitForTimeout(2000);
  await page.goto(loginBase);
  const payload = await page.evaluate(async () => {
    const [session, analytics, index] = await Promise.all([
      fetch('/api/session', { credentials: 'include' }),
      fetch('/api/analytics', { credentials: 'include' }),
      fetch('/api/documents?limit=10&offset=0', { credentials: 'include' }),
    ]);
    return {
      sessionStatus: session.status,
      sessionText: await session.text(),
      analyticsStatus: analytics.status,
      analyticsText: await analytics.text(),
      indexStatus: index.status,
      indexText: await index.text(),
    };
  });
  console.log(payload);
} finally {
  await browser.close();
}
