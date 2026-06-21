import { test, expect } from "@playwright/test";

test("homepage loads and has navigation", async ({ page }) => {
  await page.goto("/");
  await expect(page).toHaveTitle(/QuantAtlas|量化/);
});
