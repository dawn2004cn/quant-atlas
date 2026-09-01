import { test, expect } from "../fixtures/authed";

test("backtest page renders", async ({ authedPage: page }) => {
  await page.goto("/backtest");
  await expect(page.locator("body")).toBeVisible();
  await expect(page).toHaveTitle(/回测|Backtest/);
});
