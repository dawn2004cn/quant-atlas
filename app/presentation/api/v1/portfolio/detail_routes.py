"""Portfolio detail and watchlist import routes."""

from __future__ import annotations

from flask import Blueprint, request
from flask_login import login_required

from app.core.middleware.request_context import current_user_id, require_authenticated_user_id
from app.domain.enums import MarketCode
from app.presentation.api.common import ok_response
from app.presentation.api.route_deps import PortfolioRouteDeps, require_watchlist_for_portfolio
from app.presentation.api.v1_context import ApiV1Context


def _compute_portfolio_risk(holdings: list[dict]) -> dict[str, float]:
    """Derive simple risk metrics from current holdings (no mock randomness)."""
    if not holdings:
        return {}

    total_value = sum(float(h.get("value") or 0) for h in holdings)
    if total_value <= 0:
        return {}

    weights: list[float] = []
    returns: list[float] = []
    for h in holdings:
        value = float(h.get("value") or 0)
        weights.append(value / total_value)
        returns.append(float(h.get("pnl") or 0) / 100.0)

    avg_return = sum(w * r for w, r in zip(weights, returns))
    variance = sum(w * (r - avg_return) ** 2 for w, r in zip(weights, returns))
    volatility = (variance ** 0.5) * (252 ** 0.5) * 100
    sharpe = (avg_return * 252) / (volatility / 100) if volatility > 0 else 0.0
    worst_pnl = min(float(h.get("pnl") or 0) for h in holdings)
    max_drawdown = worst_pnl if worst_pnl < 0 else 0.0
    alpha = (avg_return * 252 - 0.025) * 100
    downside = sum(w * min(r, 0.0) ** 2 for w, r in zip(weights, returns))
    downside_std = (downside ** 0.5) * (252 ** 0.5)
    sortino = (avg_return * 252) / downside_std if downside_std > 0 else 0.0

    return {
        "sharpe": round(sharpe, 2),
        "max_drawdown": round(max_drawdown, 2),
        "max_drawdown_pct": round(abs(max_drawdown), 2),
        "volatility": round(volatility, 2),
        "beta": None,
        "alpha": round(alpha, 2),
        "sortino": round(sortino, 2),
    }


def register_portfolio_detail_routes(
    blueprint: Blueprint,
    ctx: ApiV1Context,
    *,
    route_deps: PortfolioRouteDeps,
) -> None:
    _ = ctx
    market_service = route_deps.market_service

    @blueprint.get("/portfolio/<portfolio_id>")
    @login_required
    def portfolio_detail(portfolio_id: str):
        """Get portfolio detail with holdings and risk metrics."""
        watchlist_service = route_deps.watchlist_service
        market_svc = market_service

        user_id = current_user_id()
        symbols = (
            watchlist_service.list_symbols(user_id=user_id)
            if watchlist_service and user_id
            else []
        )
        if not symbols:
            return ok_response(
                data={
                    "portfolio_id": portfolio_id,
                    "holdings": [],
                    "total_value": 0,
                    "total_return": 0,
                    "today_return": 0,
                    "holdings_count": 0,
                    "performance": [],
                    "industry_allocation": [],
                    "risk": {},
                },
                legacy_alias_key=None,
                enable_legacy_alias=False,
            )

        stocks = market_svc.list_quotes(MarketCode.CN, symbols) if market_svc else []
        stock_map = {str(s.get("code", s.get("symbol", ""))): s for s in stocks}

        holdings = []
        total_value = 0
        total_cost = 0

        for sym in symbols:
            s = stock_map.get(sym)
            if not s:
                continue
            price = float(s.get("price", 0) or 0)
            value = price * 100
            cost = price * 100
            total_value += value
            total_cost += cost

        for sym in symbols:
            s = stock_map.get(sym)
            if not s:
                continue
            price = float(s.get("price", 0) or 0)
            value = price * 100
            cost = price * 100
            weight = (value / total_value * 100) if total_value > 0 else 0
            holdings.append({
                "code": s.get("code", s.get("symbol", "")),
                "name": s.get("name", ""),
                "weight": round(weight, 2),
                "value": round(value, 2),
                "cost": round(price * 100, 2),
                "price": price,
                "pnl": round((value - cost) / cost * 100, 2) if cost > 0 else 0,
            })

        total_return = ((total_value - total_cost) / total_cost * 100) if total_cost > 0 else 0
        today_return = sum(float(s.get("change_pct", 0) or 0) for s in stocks) / len(stocks) if stocks else 0

        industry_map = {}
        for s in stocks:
            ind = s.get("industry", "未分类")
            industry_map[ind] = industry_map.get(ind, 0) + (float(s.get("price", 0) or 0) * 100)
        industry_allocation = [
            {"name": k, "weight": round(v / total_value * 100, 2)}
            for k, v in industry_map.items()
        ]

        perf = []
        if len(stocks) >= 2:
            base = 100
            for s in sorted(stocks, key=lambda x: float(x.get("change_pct", 0) or 0)):
                cp = float(s.get("change_pct", 0) or 0)
                base = base * (1 + cp / 100)
                perf.append({"date": "2024", "value": round(base - 100, 2)})

        risk = _compute_portfolio_risk(holdings)

        return ok_response(
            data={
                "portfolio_id": portfolio_id,
                "holdings": holdings,
                "total_value": round(total_value, 2),
                "total_return": round(total_return, 2),
                "today_return": round(today_return, 2),
                "holdings_count": len(holdings),
                "performance": perf,
                "industry_allocation": industry_allocation,
                "risk": risk,
            },
            legacy_alias_key=None,
            enable_legacy_alias=False,
        )

    @blueprint.post("/portfolio/import")
    @login_required
    def portfolio_import():
        """Import portfolio holdings from CSV or manual input."""
        data = request.get_json(silent=True) or {}
        holdings = data.get("holdings", [])
        mode = data.get("mode", "merge")

        watchlist_service = require_watchlist_for_portfolio(route_deps)
        user_id = require_authenticated_user_id()

        if mode == "replace":
            current = watchlist_service.list_symbols(user_id=user_id)
            for sym in current:
                watchlist_service.remove_symbol(user_id, sym)

        added = []
        for h in holdings:
            sym = str(h.get("symbol", "")).strip().upper()
            if sym:
                watchlist_service.add_symbol(user_id, sym)
                added.append(sym)

        return ok_response(
            data={"added": added, "count": len(added), "mode": mode},
            legacy_alias_key=None,
            enable_legacy_alias=False,
        )
