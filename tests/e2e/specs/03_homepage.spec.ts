import { test, expect } from "@playwright/test";

test("homepage loads and has navigation", async ({ page }) => {
  await page.goto("/");
  await expect(page).toHaveTitle(/Quant Atlas|操盘台|今日/);
});
