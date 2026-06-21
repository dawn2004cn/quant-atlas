from __future__ import annotations

"""Strategy recommend / copilot HTTP adapters."""

from flask import Blueprint, request
from flask_login import login_required

from ...application.errors import ValidationError
from ...core.logger import get_logger
from ...core.registry import register_routes
from ...domain.enums import MarketCode
from .common import ok_response, parse_market, require_ctx_service
from .v1_context import ApiV1Context

logger = get_logger(__name__)


def _optional_float_arg(name: str) -> float | None:
    raw = (request.args.get(name) or "").strip()
    if raw == "":
        return None
    try:
        return float(raw)
    except ValueError as exc:
        raise ValidationError(f"{name}_invalid") from exc


def _strategy_name(strategy_id: str, fallback: str = "Trend Following") -> str:
    return (strategy_id or fallback).replace("_", " ").title()


def _safe_float(value: object) -> float | None:
    try:
        return float(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def _attach_suggested_trade_plan(
    ctx: ApiV1Context,
    *,
    symbol: str,
    market: MarketCode,
    payload: dict,
) -> None:
    """Pre-fill trade plan DTO for one-click adopt on the client."""
    svc = ctx.trade_plan_service
    if svc is None:
        return
    entry_price: float | None = None
    if ctx.stock_service is not None:
        try:
            detail = ctx.stock_service.get_stock_detail(symbol, market)
            if isinstance(detail, dict):
                profile = detail.get("profile") or {}
                realtime = profile.get("realtime") if isinstance(profile, dict) else {}
            else:
                profile = getattr(detail, "profile", None) or {}
                realtime = profile.get("realtime", {}) if isinstance(profile, dict) else {}
            entry_price = _safe_float((realtime or {}).get("price"))
        except Exception as exc:  # noqa: BLE001
            logger.warning("copilot trade plan entry price: %s", exc)
    try:
        plan = svc.build_plan(
            symbol=symbol,
            market=market,
            account_equity=100000.0,
            cash_available=100000.0,
            entry_price=entry_price,
        )
        if hasattr(plan, "model_dump"):
            plan_body = plan.model_dump()
        elif hasattr(plan, "dict"):
            plan_body = plan.dict()
        else:
            plan_body = dict(plan) if isinstance(plan, dict) else {}
        payload["suggested_trade_plan"] = plan_body
        top = payload.get("top_pick") or {}
        payload["trade_plan_action"] = {
            "method": "POST",
            "href": "/api/v1/trade-plan/adopt",
            "body": {
                "symbol": symbol,
                "market": market.value,
                "source": "strategy_copilot",
                "strategy_id": top.get("strategy_id"),
                "reason": top.get("reason") or "",
            },
            "preview_href": f"/api/v1/trade-plan?symbol={symbol}&market={market.value}",
        }
    except Exception as exc:  # noqa: BLE001
        logger.warning("copilot suggested_trade_plan: %s", exc)


def _build_copilot_payload(result: dict) -> dict:
    recs = result.get("recommendations", [])
    top = recs[0] if recs else {"strategy": "trend_following", "score": 0.7}
    regime = result.get("regime", "")
    return {
        "volatility_regime": regime.split("_")[0] if "_" in regime else "analyzing",
        "trend_regime": result.get("trend", "analyzing"),
        "annual_volatility": round(result.get("volatility", 0) * 15.8, 2),
        "top_pick": {
            "strategy_id": top.get("strategy", "trend_following"),
            "name": _strategy_name(top.get("strategy", "trend_following")),
            "fit_score": int(float(top.get("score", 0.7)) * 100),
            "reason": top.get("reason", "default recommendation"),
        },
        "alternatives": [
            {
                "strategy_id": item.get("strategy"),
                "name": _strategy_name(item.get("strategy", "")),
                "fit_score": int(float(item.get("score", 0)) * 100),
            }
            for item in recs[1:4]
        ],
    }


@register_routes(name="strategy_copilot", context="strategy", description="Strategy recommend / copilot")
def register_strategy_copilot_routes(blueprint: Blueprint, ctx: ApiV1Context) -> None:
    """Register /strategy/recommend and /strategy/copilot routes."""
    legacy = ctx.enable_legacy_response_fields

    @blueprint.get("/strategy/recommend")
    @login_required
    def strategy_recommend():
        symbol = request.args.get("symbol", "").strip()
        market = parse_market(request.args.get("market", "CN"))
        if not symbol:
            raise ValidationError("symbol_required")
        svc = require_ctx_service(ctx, "recommendation_service")
        data = svc.daily_top(market=market, top_n=10)
        return ok_response(legacy_alias_key=None, enable_legacy_alias=legacy, data=data)

    @blueprint.get("/strategy/copilot")
    @login_required
    def strategy_copilot():
        """Return strategy fit plus shadow evaluation and handover suggestion."""
        symbol = request.args.get("symbol", "").strip()
        market_raw = request.args.get("market", "CN").strip().upper()
        if not symbol:
            raise ValidationError("symbol_required")

        try:
            market = MarketCode(market_raw)
        except (ValueError, KeyError):
            market = MarketCode.CN

        try:
            copilot_svc = getattr(ctx, "strategy_copilot_service", None)
            if copilot_svc is not None:
                eval_payload = copilot_svc.evaluate(
                    symbol,
                    market,
                    active_strategy_id=(request.args.get("active_strategy") or "").strip() or None,
                )
                if not eval_payload.get("ok"):
                    raise ValidationError(eval_payload.get("error", "analysis_failed"))
                result = eval_payload.get("analysis") or {}
                payload = _build_copilot_payload(result)
                payload["shadow_strategies"] = eval_payload.get("shadow_strategies", [])
                payload["active_strategy"] = eval_payload.get("active_strategy")
                payload["handover"] = eval_payload.get("handover")
                payload["arbiter"] = {
                    "verdict": (eval_payload.get("arbiter") or {}).get("verdict"),
                    "confidence": (eval_payload.get("arbiter") or {}).get("confidence"),
                    "provenance_id": (eval_payload.get("arbiter") or {}).get("provenance_id"),
                }
            else:
                from app.application.use_cases.strategy_copilot_use_case import (
                    get_strategy_copilot_use_case,
                )

                result = get_strategy_copilot_use_case().execute(symbol, market)
                if "error" in result:
                    raise ValidationError(result.get("error", "analysis_failed"))
                payload = _build_copilot_payload(result)
            sandbox_requested = any(
                request.args.get(name) is not None
                for name in ("market_shock_pct", "volatility_threshold", "stop_loss_pct")
            )
            if sandbox_requested:
                from app.modules.strategy.services.strategy.sensitivity_sandbox_service import (
                    SensitivitySandboxService,
                )

                payload["sensitivity_sandbox"] = SensitivitySandboxService().simulate(
                    result,
                    market_shock_pct=_optional_float_arg("market_shock_pct") or 0.0,
                    volatility_threshold=_optional_float_arg("volatility_threshold"),
                    stop_loss_pct=_optional_float_arg("stop_loss_pct"),
                )

            _attach_suggested_trade_plan(ctx, symbol=symbol, market=market, payload=payload)

            return ok_response(
                data=payload,
                legacy_alias_key=None,
                enable_legacy_alias=legacy,
            )
        except Exception as e:
            logger.error(f"strategy_copilot error: {symbol} {market} - {e}")
            return ok_response(
                data={
                    "volatility_regime": "analyzing",
                    "trend_regime": "analyzing",
                    "top_pick": {
                        "strategy_id": "trend_following",
                        "name": "Trend Following",
                        "fit_score": 70,
                        "reason": "default recommendation",
                    },
                },
                legacy_alias_key=None,
                enable_legacy_alias=legacy,
            )

    @blueprint.post("/strategy/copilot/handover")
    @login_required
    def strategy_copilot_handover():
        """One-click switch from active strategy to shadow winner."""
        svc = require_ctx_service(ctx, "strategy_copilot_service")
        body = request.get_json(silent=True) or {}
        symbol = (body.get("symbol") or "").strip()
        to_strategy = (body.get("to_strategy") or "").strip()
        if not symbol or not to_strategy:
            raise ValidationError("symbol_and_to_strategy_required")
        market = (body.get("market") or "CN").strip().upper()
        payload = svc.apply_handover(symbol, to_strategy, market)
        return ok_response(data=payload, legacy_alias_key=None, enable_legacy_alias=legacy)
