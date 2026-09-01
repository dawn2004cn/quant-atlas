import { test as base, expect } from "@playwright/test";
import { TEST_USER } from "./test_user";

async function loginViaClassicForm(
  page: import("@playwright/test").Page,
  baseURL: string,
) {
  await page.goto(`${baseURL}/login`);
  await page.fill("input[name='username']", TEST_USER.username);
  await page.fill("input[name='password']", TEST_USER.password);
  await page.click("button[type='submit']");
  await page.waitForURL((url) => !url.pathname.endsWith("/login"), {
    timeout: 15_000,
  });
}

export const test = base.extend({
  authedPage: async ({ page, baseURL }, use) => {
    await loginViaClassicForm(page, baseURL ?? "http://127.0.0.1:5000");
    await use(page);
  },
});

export { expect };
