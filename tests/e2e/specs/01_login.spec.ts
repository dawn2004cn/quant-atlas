import { test, expect } from "@playwright/test";
import { TEST_USER } from "../fixtures/test_user";

test.use({ storageState: { cookies: [], origins: [] } });

test("Flask login page renders", async ({ page }) => {
  await page.goto("/login");
  await expect(page.locator("input[name='username']")).toBeVisible();
  await expect(page.locator("input[name='password']")).toBeVisible();
});

test("SPA login page renders", async ({ page }) => {
  await page.goto("/app/login");
  await expect(page.locator("input#username")).toBeVisible();
  await expect(page.locator("input#password")).toBeVisible();
  await expect(page.locator("button[type='submit']")).toBeVisible();
  // Mode tabs visible
  await expect(page.locator("button", { hasText: "Session" })).toBeVisible();
  await expect(page.locator("button", { hasText: "API Token" })).toBeVisible();
});

test("SPA login shows error for invalid credentials", async ({ page }) => {
  await page.goto("/app/login");
  await page.fill("input#username", "nonexistent-user");
  await page.fill("input#password", "wrong-password");
  await page.click("button[type='submit']");
  // Error message should appear
  await expect(page.locator("text=/登录失败|invalid_credentials|Unauthorized|用户名或密码|错误/i")).toBeVisible({ timeout: 5_000 });
});

test("switcher: Flask → SPA roundtrip", async ({ page }) => {
  // 1. Navigate to Flask login page
  await page.goto("/login");
  await expect(page.locator("input[name='username']")).toBeVisible();

  // 2. Verify switcher link exists with data-spa-switcher attribute
  const switcherLink = page.locator("a[data-spa-switcher='login']");
  await expect(switcherLink).toBeVisible();

  // 3. Click switcher link
  await switcherLink.click();

  // 4. Assert SPA login page loaded
  await expect(page).toHaveURL(/\/app\/login/);
  await expect(page.locator("input#username")).toBeVisible();

  // 5. Verify "回到经典版" or "使用经典登录页" link exists
  const backToClassic = page.locator("a[href='/login']");
  await expect(backToClassic).toBeVisible();

  // 6. Click back to classic
  await backToClassic.click();

  // 7. Assert back on Flask login page
  await expect(page).toHaveURL(/\/login/);
  await expect(page.locator("input[name='username']")).toBeVisible();
});
