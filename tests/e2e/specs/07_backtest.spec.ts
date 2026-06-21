import { test, expect } from "@playwright/test";

test("backtest page renders", async ({ page }) => {
  await page.goto("/backtest");
  await expect(page.locator("body")).toBeVisible();
  await expect(page).toHaveTitle(/回测|Backtest/);
});
