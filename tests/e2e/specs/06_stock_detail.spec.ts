import { test, expect } from "../fixtures/authed";

test("stock detail page loads with symbol", async ({ authedPage: page }) => {
  // domcontentloaded: this page has a large inline script plus vendor charts.
  // waitUntil=load waits for every leftover stylesheet/script and flakes in CI.
  await page.goto("/stock/000001", { waitUntil: "domcontentloaded" });
  await expect(page.locator("body")).toBeVisible();
  await expect(page).toHaveTitle(/000001|平安银行|Stock/);
});
