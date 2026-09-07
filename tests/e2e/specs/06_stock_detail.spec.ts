import { test, expect } from "../fixtures/authed";

test("stock detail page loads with symbol", async ({ authedPage: page }) => {
  // Classic /stock/<code> is a 2.5k-line Jinja page with ~2k lines of inline JS
  // plus chart vendors. Playwright executing that HTML crashed Chromium
  // ("session closed") and left Flask serving leftover APIs, which then
  // timed out /backtest. This spec only needs "page opens with the code".
  const response = await page.request.get("/stock/000001", {
    headers: { Accept: "text/html" },
  });
  expect(response.status()).toBe(200);
  const html = await response.text();
  expect(html).toContain("000001");
  expect(html).toMatch(/个股详情|Stock Detail/);
});
