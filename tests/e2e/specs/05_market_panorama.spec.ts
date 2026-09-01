import { test, expect } from "../fixtures/authed";

test("market panorama page renders", async ({ authedPage: page }) => {
  await page.goto("/market-panorama");
  await expect(page.locator("body")).toBeVisible();
  await expect(page).toHaveTitle(/市场全景|Market|Panorama/);
});
