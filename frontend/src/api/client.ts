/**
 * API client skeleton for QuantAtlas.
 *
 * Types are auto-generated from docs/openapi.json via:
 *   npm run gen:api-types
 *
 * Usage:
 *   import { whoami } from "./api/client";
 *   const user = await whoami();
 */
import type { paths } from "./types";

type WhoamiResponse =
  paths["/api/v1/auth/whoami"]["get"]["responses"]["200"]["content"]["application/json"];

export async function whoami(): Promise<WhoamiResponse | null> {
  const resp = await fetch("/api/v1/auth/whoami", { credentials: "include" });
  if (resp.status === 401) return null;
  if (!resp.ok) throw new Error(`whoami failed: ${resp.status}`);
  return resp.json();
}
