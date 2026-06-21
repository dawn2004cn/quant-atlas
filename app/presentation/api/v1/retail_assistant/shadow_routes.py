"""Retail assistant shadow mirroring route."""

from __future__ import annotations

from flask import Blueprint, request
from flask_login import current_user, login_required

from app.modules.ai_agent.services.advanced_features_service import ShadowMirroringService
from app.modules.system.services.helpers.shadow_portfolio_weights import (
    build_cost_basis_map,
    build_weights_from_watchlist,
    estimate_position_weights,
    merge_position_weights,
)
import logging
logger = logging.getLogger(__name__)
from app.presentation.api.common import ok_response, parse_market
from app.presentation.api.v1.retail_assistant.runtime import RetailAssistantRuntime
from app.presentation.api.v1_context import ApiV1Context


def register_retail_assistant_shadow_routes(
    blueprint: Blueprint,
    ctx: ApiV1Context,
    *,
    runtime: RetailAssistantRuntime,
) -> None:
    legacy = runtime.legacy

    @blueprint.get("/retail-assistant/shadow-mirror")
    @login_required
    def retail_assistant_shadow_mirror():
        """影子操盘：大师风格模拟建议（结合行情与自选/持仓）。"""
        market = parse_market(request.args.get("market", "CN"))
        symbols = [s.strip() for s in request.args.getlist("symbol") if s.strip()]
        if not symbols:
            raw = (request.args.get("symbols") or "").strip()
            symbols = [x.strip() for x in raw.replace(";", ",").split(",") if x.strip()]

        holding_codes: list[str] = []
        user_id = int(getattr(current_user, "id", None) or 0)
        if user_id and getattr(ctx, "watchlist_service", None) is not None:
            try:
                holding_codes.extend(ctx.watchlist_service.list_symbols(user_id=user_id))
            except Exception:  # noqa: BLE001
                logger.warning("Suppressed exception in register_retail_assistant_shadow_routes", exc_info=True)
                pass
        portfolio_svc = getattr(ctx, "portfolio_service", None) or getattr(
            ctx, "portfolio_application_service", None
        )
        if user_id and portfolio_svc is not None and hasattr(portfolio_svc, "get_user_portfolio"):
            try:
                pf = portfolio_svc.get_user_portfolio(user_id=user_id)
                for h in getattr(pf, "holdings", None) or []:
                    sym = getattr(h, "symbol", None) or (h.get("symbol") if isinstance(h, dict) else None)
                    if sym:
                        holding_codes.append(str(sym))
            except Exception:  # noqa: BLE001
                logger.warning("Suppressed exception in register_retail_assistant_shadow_routes", exc_info=True)
                pass
        holding_codes = list({str(c).strip() for c in holding_codes if str(c).strip()})

        quotes: list[dict] = []
        market_svc = None
        if getattr(ctx, "market", None) is not None:
            market_svc = getattr(ctx.market, "market_service", None)
        market_svc = market_svc or getattr(ctx, "market_service", None)
        if symbols and market_svc is not None:
            try:
                quotes = list(market_svc.list_quotes(market, symbols) or [])
            except Exception:  # noqa: BLE001
                quotes = []

        wl_weights: dict[str, float] = {}
        if user_id and getattr(ctx, "watchlist_service", None) is not None and market_svc is not None:
            wl_weights = build_weights_from_watchlist(
                user_id=user_id,
                watchlist_service=ctx.watchlist_service,
                market_service=market_svc,
                market=market,
            )
        position_weights = merge_position_weights(
            estimate_position_weights(holding_codes, quotes),
            wl_weights,
        )
        investor_profile: dict = {}
        profile_svc = getattr(ctx, "user_investment_profile_service", None)
        if user_id and profile_svc is not None:
            try:
                investor_profile = profile_svc.get_profile(user_id) or {}
            except Exception:  # noqa: BLE001
                investor_profile = {}
        cost_basis: dict[str, dict] = {}
        trade_svc = getattr(ctx, "portfolio_trade_service", None)
        if user_id and trade_svc is not None and hasattr(trade_svc, "calculate_holdings"):
            try:
                cost_basis = build_cost_basis_map(trade_svc.calculate_holdings(user_id))
            except Exception:  # noqa: BLE001
                cost_basis = {}
        payload = ShadowMirroringService().mirror_with_masters(
            symbols,
            quotes=quotes,
            holding_codes=holding_codes,
            position_weights=position_weights,
            investor_profile=investor_profile,
            cost_basis=cost_basis,
        )
        return ok_response(data=payload, legacy_alias_key=None, enable_legacy_alias=legacy)
