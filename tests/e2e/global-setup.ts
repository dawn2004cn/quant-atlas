import { request, type FullConfig } from "@playwright/test";
import fs from "fs";
import path from "path";

const AUTH_FILE = path.join(__dirname, ".auth/user.json");

async function globalSetup(config: FullConfig) {
  const baseURL =
    (config.projects[0]?.use?.baseURL as string | undefined) ??
    process.env.E2E_BASE_URL ??
    "http://127.0.0.1:5000";
  const username = process.env.E2E_USERNAME ?? "admin";
  const password = process.env.E2E_PASSWORD ?? "admin123";

  fs.mkdirSync(path.dirname(AUTH_FILE), { recursive: true });

  const ctx = await request.newContext({ baseURL });
  const loginPage = await ctx.get("/login");
  if (!loginPage.ok()) {
    throw new Error(`Failed to load /login: HTTP ${loginPage.status()}`);
  }
  const html = await loginPage.text();
  const csrfMatch =
    html.match(/name="csrf_token"\s+value="([^"]+)"/i) ??
    html.match(/name="csrf-token"\s+content="([^"]+)"/i);
  if (!csrfMatch?.[1]) {
    throw new Error("CSRF token not found on /login");
  }
  const csrf = csrfMatch[1];

  const loginResp = await ctx.post("/login", {
    headers: {
      Referer: `${baseURL}/login`,
      "X-CSRF-Token": csrf,
    },
    form: {
      username,
      password,
      csrf_token: csrf,
    },
  });
  if (!loginResp.ok() && loginResp.status() !== 302) {
    throw new Error(`Login failed: HTTP ${loginResp.status()}`);
  }

  const whoami = await ctx.get("/api/v1/auth/whoami");
  if (!whoami.ok()) {
    throw new Error(`Session not established after login: HTTP ${whoami.status()}`);
  }

  await ctx.storageState({ path: AUTH_FILE });
  await ctx.dispose();
}

export default globalSetup;
