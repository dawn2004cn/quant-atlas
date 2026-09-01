/**
 * E2E tests for Flask↔SPA switcher grayscale mechanism.
 */
import { test, expect } from "@playwright/test";

test.use({ storageState: { cookies: [], origins: [] } });

const PUBLIC_FLASK_PAGES = [
  { path: "/login", slug: "login" },
];

for (const { path, slug } of PUBLIC_FLASK_PAGES) {
  test(`switcher roundtrip: ${path} → /app${path} → ${path}`, async ({ page }) => {
    await page.goto(path);

    const switcherLink = page.locator(`a[data-spa-switcher='${slug}']`);
    await expect(switcherLink).toBeVisible();
    await expect(switcherLink).toHaveText(/试试新版/);

    await switcherLink.click();

    await expect(page).toHaveURL(new RegExp(`/app${path.replace(/\/$/, "")}`));

    const backToClassic = page.locator("a[href='/login']");
    await expect(backToClassic).toBeVisible();

    await backToClassic.click();

    await expect(page).toHaveURL(new RegExp(path));
  });
}

test("switcher telemetry endpoint accepts POST", async ({ request }) => {
  const resp = await request.post("/api/v1/telemetry/switcher", {
    data: { event: "switch_to_spa", page: "test" },
  });
  expect([200, 202, 204]).toContain(resp.status());
});
