import { test, expect } from "../fixtures/authed";

test("homepage loads and has navigation", async ({ authedPage: page }) => {
  await page.goto("/");
  await expect(page).toHaveTitle(/Quant Atlas|操盘台|今日/);
});
