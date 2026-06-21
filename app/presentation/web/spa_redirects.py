"""Jinja → SPA redirects for migrated pages.

Per the Flask → SPA migration design:
- Phase 1 (gray period): 302 Found — browser doesn't cache, server logs check
- Phase 2 (permanent): 301 Moved Permanently — browser caches, search updates

Current status: Phase 1 (302) for all M1 migrated pages.
"""

from __future__ import annotations

from flask import Blueprint, redirect
from flask_login import login_required

_SPA_BASE = "/app"


def _spa(route: str) -> str:
    return f"{_SPA_BASE}/{route.lstrip('/')}"


def register_spa_redirects(blueprint: Blueprint) -> None:
    """Register 302 redirects from old Jinja routes to new SPA routes."""

    # ── M1: Core Flow (14 pages) ──
    _M1_REDIRECTS: dict[str, str] = {
        "/portfolio": "portfolio",
        "/self-stocks": "self-stocks",
        "/hot-sectors": "hot-sectors",
        "/global-radar": "global-radar",
        "/stock-selector": "stock-selector",
        "/long-term-select": "long-term-select",
        "/strategy-compare": "strategy-compare",
        "/strategy-snapshots": "strategy-snapshots",
        "/nl-strategy": "nl-strategy",
        "/strategy-wizard": "strategy-wizard",
        "/tdx-blocks": "tdx-blocks",
    }

    for old_route, spa_route in _M1_REDIRECTS.items():
        # Dynamic route registration to avoid 88 repetitive decorators
        _register_302(blueprint, old_route, spa_route)

    # ── Routes with path parameters ──
    @blueprint.route("/portfolio/<portfolio_id>")
    @login_required
    def portfolio_detail_redirect(portfolio_id: str):
        return redirect(_spa(f"portfolio/{portfolio_id}"), code=302)

    @blueprint.route("/decision-snapshot/<snapshot_id>")
    @login_required
    def decision_snapshot_redirect(snapshot_id: str):
        return redirect(_spa(f"decision-snapshot/{snapshot_id}"), code=302)

    @blueprint.route("/share/decision/<share_token>")
    def decision_snapshot_public_redirect(share_token: str):
        return redirect(_spa(f"share/decision/{share_token}"), code=302)


def _register_302(blueprint: Blueprint, old_route: str, spa_route: str) -> None:
    """Register a single 302 redirect from old_route to /app/spa_route."""

    def _make_handler(target: str):
        @login_required
        def _handler():
            return redirect(_spa(target), code=302)
        _handler.__name__ = f"redirect_{target.replace('/', '_').replace('-', '_')}"
        return _handler

    blueprint.add_url_rule(old_route, endpoint=None, view_func=_make_handler(spa_route))
