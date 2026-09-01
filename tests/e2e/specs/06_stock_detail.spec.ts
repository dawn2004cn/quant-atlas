import { test, expect } from "../fixtures/authed";

test("stock detail page loads with symbol", async ({ authedPage: page }) => {
  await page.goto("/stock/000001");
  await expect(page.locator("body")).toBeVisible();
  await expect(page).toHaveTitle(/000001|平安银行|Stock/);
});
