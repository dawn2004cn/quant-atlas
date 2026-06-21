import { test, expect } from "@playwright/test";

test("health endpoint returns 200", async ({ request }) => {
  const resp = await request.get("/api/v1/system/health");
  expect(resp.ok()).toBeTruthy();
  const body = await resp.json();
  expect(body).toHaveProperty("status");
});
