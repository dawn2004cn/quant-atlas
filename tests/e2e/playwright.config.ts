import { defineConfig, devices } from "@playwright/test";
import path from "path";

const AUTH_FILE = path.join(__dirname, ".auth/user.json");

export default defineConfig({
  testDir: "./specs",
  globalSetup: require.resolve("./global-setup"),
  timeout: 30_000,
  expect: { timeout: 5_000 },
  fullyParallel: false,
  retries: process.env.CI ? 2 : 0,
  workers: 1,
  reporter: process.env.CI ? "github" : "list",
  use: {
    baseURL: process.env.E2E_BASE_URL ?? "http://127.0.0.1:5000",
    storageState: AUTH_FILE,
    trace: "on-first-retry",
    screenshot: "only-on-failure",
    video: "retain-on-failure",
  },
  projects: [
    { name: "chromium", use: { ...devices["Desktop Chrome"] } },
  ],
});
