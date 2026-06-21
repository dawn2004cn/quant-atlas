import { test, expect } from "@playwright/test";

test("market panorama page renders", async ({ page }) => {
  await page.goto("/market-panorama");
  await expect(page.locator("body")).toBeVisible();
  await expect(page).toHaveTitle(/市场全景|Market|Panorama/);
});
