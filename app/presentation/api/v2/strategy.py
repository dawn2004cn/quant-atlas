from __future__ import annotations

from flask import Blueprint, request

from app.core.composite_rate_limiter import LimitRule, require_rate_limit

from ....domain.enums import MarketCode
from ..auth_guard import api_auth_required
from ..responses import success_response


def create_strategy_blueprint(ctx):
    bp = Blueprint("v2_strategy", __name__)

    @bp.post("/backtest")
    @api_auth_required
    @require_rate_limit(
        LimitRule(max_calls=5, window_seconds=60, key_prefix="backtest"),
    )
    def run_backtest():
        from ....application.dto import BacktestRequestDTO
        from .request_parsers import parse_dto
        body = request.get_json(silent=True) or {}
        if ctx.enable_dto_validation:
            dto = parse_dto(body, BacktestRequestDTO)
            payload = {
                "symbol": dto.symbol,
                "strategy_name": dto.strategy_name,
                "start": dto.start,
                "end": dto.end,
                "initial_capital": dto.initial_capital,
            }
        else:
            payload = {
                "symbol": body.get("symbol", ""),
                "strategy_name": body.get("strategy", "MA"),
                "start": body.get("start", ""),
                "end": body.get("end", ""),
                "initial_capital": body.get("initial_capital", 100000),
            }

        if ctx.backtest_facade is not None:
            run_async = str(request.args.get("async", "")).lower() in {"1", "true", "yes"}
            if run_async:
                client_key = (
                    (request.headers.get("Idempotency-Key") or "").strip()
                    or str(body.get("idempotency_key") or "").strip()
                    or None
                )
                result = ctx.backtest_facade.run_backtest_async(
                    **payload,
                    client_idempotency_key=client_key,
                )
            else:
                result = ctx.backtest_facade.run_backtest(**payload)
        else:
            result = ctx.strategy_service.backtest(
                symbol=payload["symbol"],
                strategy_name=payload["strategy_name"],
                start=payload["start"],
                end=payload["end"],
                initial_capital=payload["initial_capital"],
            )
        return success_response(data=result, meta={"version": "v2"})

    @bp.post("/backtest/compare")
    @api_auth_required
    def compare_backtests():
        from ....application.dto import BacktestCompareRequestDTO
        from .request_parsers import parse_dto

        body = request.get_json(silent=True) or {}
        if ctx.enable_dto_validation:
            dto = parse_dto(body, BacktestCompareRequestDTO)
            payload = {
                "symbol": dto.symbol,
                "strategies": dto.strategies,
                "start": dto.start,
                "end": dto.end,
                "initial_capital": dto.initial_capital,
            }
        else:
            strategies = body.get("strategies") or body.get("strategy_names") or []
            if isinstance(strategies, str):
                strategies = [s.strip() for s in strategies.split(",") if s.strip()]
            payload = {
                "symbol": body.get("symbol", ""),
                "strategies": strategies,
                "start": body.get("start", body.get("start_date", "")),
                "end": body.get("end", body.get("end_date", "")),
                "initial_capital": body.get("initial_capital", 100000),
            }

        if ctx.backtest_facade is None:
            from ....application.errors import ValidationError
            raise ValidationError("Backtest facade not configured")

        result = ctx.backtest_facade.compare_strategies(**payload)
        return success_response(data=result, meta={"version": "v2"})

    @bp.get("/select")
    @api_auth_required
    def select_stocks():
        from ....application.dto import SelectionRequestDTO
        from .request_parsers import parse_dto
        if ctx.enable_dto_validation:
            dto = parse_dto(request.args.to_dict(), SelectionRequestDTO, partial=True)
            market = MarketCode(dto.market)
            strategy_name = dto.strategy
            top_n = dto.top_n
        else:
            strategy_name = request.args.get("strategy", "classic")
            market_str = request.args.get("market", "CN")
            try:
                market = MarketCode(market_str)
            except ValueError:
                from ....application.errors import ValidationError
                raise ValidationError(f"Invalid market: {market_str}") from None
            top_n = int(request.args.get("top_n", 20))

        if ctx.backtest_facade is not None:
            result = ctx.backtest_facade.select_stocks(
                strategy_name=strategy_name,
                market=market,
                top_n=top_n,
            )
        else:
            result = ctx.strategy_service.select_stocks(
                strategy_name=strategy_name,
                market=market,
                top_n=top_n,
            )

        return success_response(
            data={"candidates": result.get("candidates", [])},
            meta={"strategy": strategy_name},
        )

    @bp.get("/")
    @api_auth_required
    def list_strategies():
        result = ctx.strategy_service.list_strategies()
        return success_response(data=result)

    @bp.get("/<name>")
    @api_auth_required
    def get_strategy(name: str):
        result = ctx.strategy_service.get_strategy(name)
        return success_response(data=result, meta={"strategy": name})

    # ------------------------------------------------------------------
    # Strategy SOP Management Endpoints
    # ------------------------------------------------------------------
    @bp.post("/sop/<symbol>")
    @api_auth_required
    def set_symbol_sop(symbol: str):
        body = request.get_json(silent=True) or {}
        archetype = body.get("archetype", "conservative")
        ctx.strategy_sop_service.set_archetype(symbol, archetype)
        return success_response(data={"symbol": symbol, "archetype": archetype})

    @bp.get("/sop/<symbol>")
    @api_auth_required
    def get_symbol_sop(symbol: str):
        archetype = ctx.strategy_sop_service.get_archetype(symbol)
        return success_response(data={"symbol": symbol, "archetype": archetype})

    return bp
