# API v1 Route Contract

Canonical contract for `/api/v1/*` paths used by templates, SPA, and CI gates.

**Source of truth in code:**

| Artifact | Path | Role |
|----------|------|------|
| Critical paths | `app/presentation/api/route_contract.py` → `CRITICAL_ROUTE_MODULES` | Boot-time registration + `audit_api_routes.py` |
| Legacy aliases | `route_contract.py` → `LEGACY_PATH_ALIASES` | Wrong Phase-2 prefixes kept for backward compat |
| Public (no auth) | `app/presentation/api/public_api_paths.py` | Anonymous GET allowlist |
| Template fetch | `route_contract.collect_template_fetch_paths()` | HTML `fetch('/api/v1/...')` audit |
| SPA fetch | `scripts/audit_frontend_api_paths.py` | React `api.ts` / page components |

## Verification (run before merge)

```bash
python scripts/boot_gate.py
python scripts/audit_api_routes.py
python scripts/audit_frontend_api_paths.py
python scripts/check_module_cross_imports.py
pytest tests/api/test_api_contract.py tests/api/test_public_api_contract.py tests/api/test_template_fetch_contract.py -q
```

## Public endpoints (GET, no login)

| Path | Notes |
|------|-------|
| `/api/v1/compliance/manifest` | Retail compliance copy |
| `/api/v1/health` | Liveness |
| `/api/v1/system/health` | Capabilities + `deployment_status` (ok/degraded/critical) |

All other `/api/v1/*` routes expect Flask-Login session or v2 JWT unless documented otherwise.

**`/api/v1/system/health` body (public):**

```json
{
  "status": "ok",
  "deployment_status": "ok | degraded | critical",
  "services": {
    "required_missing": [],
    "optional_missing": [],
    "critical_missing": []
  }
}
```

`status` is always `ok` when the process serves HTTP (liveness). `deployment_status` reflects wired services per `service_readiness.py`.

## Critical canonical paths (CI gate)

These must register on the main v1 blueprint (see `CRITICAL_ROUTE_MODULES` for full list):

| Path | Module |
|------|--------|
| `/api/v1/jarvis/proactive` | `routes_v1_jarvis` |
| `/api/v1/system/task-messages` | `routes_v1_task_ops` |
| `/api/v1/system/active-jobs` | `routes_v1_task_ops` |
| `/api/v1/compliance/manifest` | `routes_v1_compliance` |
| `/api/v1/data/timeseries-health` | `routes_v1_data_infrastructure` |
| `/api/v1/data/timeseries-sync-history` | `routes_v1_data_infrastructure` |
| `/api/v1/backtest` | `routes_v1_quant_ai` |
| `/api/v1/nl/query`, `/api/v1/nl-parser/query` | `routes_v1_nl` |
| `/api/v1/integration/stack-status` | `routes_v1_integration_stack` |
| `/api/v1/system/health` | `routes_v1_system_health` |
| `/api/v1/realtime/status` | `routes_v1_realtime` |
| `/api/v1/zen-mode/zen/search` (+ toggle, resonance) | `routes_v1_zen_mode` |
| `/api/v1/provenance/truth-dashboard` | `routes_v1_provenance` |
| `/api/v1/system/alerts/dispatch` | `routes_v1_alert_center` |
| `/api/v1/shadow-account/status`, `/analyze` | `routes_v1_shadow_account` |
| `/api/v1/alpha/marketplace/listings`, `/orders` | `routes_v1_alpha_marketplace` |
| `/api/v1/alpha/reputation/balance`, `/alpha/wallet/balance` | `routes_v1_alpha_marketplace` |

## Legacy path aliases

Clients may still call aliased paths; Flask registers both:

| Alias (legacy) | Canonical |
|----------------|-----------|
| `/api/v1/ai-agent/jarvis/proactive` | `/api/v1/jarvis/proactive` |
| `/api/v1/ai-agent/backtest` | `/api/v1/backtest` |
| `/api/v1/system/system/task-messages` | `/api/v1/system/task-messages` |
| `/api/v1/data/data/timeseries-health` | `/api/v1/data/timeseries-health` |
| `/api/v1/system/compliance/manifest` | `/api/v1/compliance/manifest` |
| `/api/v1/phase18/zen/search` | `/api/v1/zen-mode/zen/search` |

Full table: `LEGACY_PATH_ALIASES` in `route_contract.py`.

## Optional services & degraded responses

Bootstrap tiers (`service_readiness.py`):

- **REQUIRED** — missing → strict boot fails (`market_service`, `stock_service`, `watchlist_service`, `stock_group_service`)
- **OPTIONAL** — missing → log debug; routes return `data.available=false` + `data.code=service_unavailable` via `@service_fallback` or `@deps_service_fallback`
- **FEATURE_FLAG** — qlib / rdagent / strategy_optimization; never fail boot

## Response shapes

| Surface | Format |
|---------|--------|
| v1 (most routes) | `ok_response` / `ok_resource` — legacy alias optional |
| v2 | `{ok, data, meta}` via `responses.success_response` |
| Service missing (v1 fallback) | HTTP 200 + `data.available=false` + `data.code=service_unavailable` (graceful UI) |
| Self-healing execution | v2-style `ErrorCode` envelope (intentional) |

## Adding a new critical path

1. Implement route on main `/api/v1` blueprint.
2. Add `RouteModuleSpec` to `CRITICAL_ROUTE_MODULES` if templates/SPA depend on it.
3. If SPA uses it, add to `audit_frontend_api_paths.py` manifest.
4. Run verification commands above.
5. Append entry to `REFACTORING_LOG.md`.
