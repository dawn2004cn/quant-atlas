import { test, expect } from "@playwright/test";
import { TEST_USER } from "../fixtures/test_user";

test("login page renders", async ({ page }) => {
  await page.goto("/login");
  await expect(page.locator("input[name='username']")).toBeVisible();
  await expect(page.locator("input[name='password']")).toBeVisible();
});
