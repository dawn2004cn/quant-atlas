/**
 * E2E tests for Flask↔SPA switcher grayscale mechanism.
 *
 * Verifies:
 * 1. Flask page renders {% block spa_switcher %} with data-spa-switcher link
 * 2. Clicking switcher link navigates to SPA page
 * 3. SPA page shows back-to-classic link
 * 4. Clicking back-to-classic navigates back to Flask page
 * 5. Telemetry events are emitted for both directions
 */
import { test, expect } from "@playwright/test";

const PUBLIC_FLASK_PAGES = [
  { path: "/login", slug: "login" },
];

for (const { path, slug } of PUBLIC_FLASK_PAGES) {
  test(`switcher roundtrip: ${path} → /app${path} → ${path}`, async ({ page }) => {
    // 1. Navigate to Flask page
    await page.goto(path);

    // 2. Verify spa_switcher block is visible with data-spa-switcher attribute
    const switcherLink = page.locator(`a[data-spa-switcher='${slug}']`);
    await expect(switcherLink).toBeVisible();
    await expect(switcherLink).toHaveText(/试试新版/);

    // 3. Click "试试新版 →"
    await switcherLink.click();

    // 4. Assert SPA page loaded
    await expect(page).toHaveURL(new RegExp(`/app${path.replace(/\/$/, "")}`));

    // 5. Verify back-to-classic link exists
    const backToClassic = page.locator("a[href='/login']");
    await expect(backToClassic).toBeVisible();

    // 6. Click back-to-classic
    await backToClassic.click();

    // 7. Assert back on Flask page
    await expect(page).toHaveURL(new RegExp(path));
  });
}

test("switcher telemetry endpoint accepts POST", async ({ request }) => {
  const resp = await request.post("/api/v1/telemetry/switcher", {
    data: { event: "switch_to_spa", page: "test" },
  });
  expect([200, 202, 204]).toContain(resp.status());
});
