# Legacy Status

## Active Entrypoints

- Main app: `run.py`
- Flask factory: `app/bootstrap.py`
- Standard API: `/api/v1/*`

## Deprecated Surface

- Compatibility API: `app/presentation/api/legacy_routes.py`
  - Kept only for a minimal transition surface.
  - Current legacy routes:
    - `/api/stocks`
    - `/api/stock/<symbol>`
    - `/api/history/<symbol>`
    - `/api/backtest`
    - `/api/watchlist`
    - `/api/watchlist/<symbol>`

## Archived Files

- `scripts/web_app.py`
  - Old monolithic Flask app.
  - Kept as migration reference only.
- `scripts/templates/detail.html`
  - Historical detail page template.
  - Not used by the new Flask page blueprint.
  - Legacy access now redirects through `/detail/<symbol>` to `/stock/<symbol>`.

## Current Storage

- Users: SQLite
- Watchlist: SQLite
- Stock groups: SQLite

## Notes

- New feature work should be added in `app/` only.
- If a legacy capability must be reused, wrap it behind domain ports and infrastructure providers rather than extending `scripts/web_app.py`.
- Full inventory of `scripts/` / `stock-analysis/` / `TradingAgents-CN-lastest` vs the platform: [scripts_inventory.md](scripts_inventory.md).
