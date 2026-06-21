"""Strategy selection and backtest routes."""

from __future__ import annotations

from flask import Blueprint, request
from flask_login import login_required

from app.presentation.api.common import ok_collection, ok_resource, parse_market
from app.presentation.api.request_parsers import parse_float_param, parse_int_param
from app.presentation.api.v1.quant_ai.runtime import QuantAiRuntime
from app.presentation.api.v1_context import ApiV1Context


def register_quant_ai_strategy_routes(
    blueprint: Blueprint,
    ctx: ApiV1Context,
    *,
    runtime: QuantAiRuntime,
) -> None:
    _ = ctx
    legacy = runtime.legacy

    @blueprint.get("/strategies/select")
    def select_stocks():
        svc = runtime.require_strategy_service()
        strategy_name = request.args.get("strategy", "classic")
        market = parse_market(request.args.get("market", "CN"))
        top_n = parse_int_param(request.args.get("top_n"), name="top_n", default=20, min_value=1)
        payload = svc.select_stocks(strategy_name, market, top_n)
        return ok_collection(
            items=payload.get("candidates", []),
            item_key="candidates",
            enable_legacy_alias=legacy,
            strategy=strategy_name,
            market=market.value,
        )

    @blueprint.post("/strategies/backtest")
    @login_required
    def run_backtest():
        svc = runtime.require_strategy_service()
        payload = request.get_json(silent=True) or {}
        result = svc.backtest(
            symbol=payload.get("symbol", ""),
            strategy_name=payload.get("strategy", "MA"),
            start=payload.get("start", ""),
            end=payload.get("end", ""),
            initial_capital=parse_float_param(
                payload.get("initial_capital"),
                name="initial_capital",
                default=100000,
                min_value=0,
            ),
        )
        runtime.push_task(
            event="strategy_backtest_completed",
            task_name="inline.strategy_backtest",
            detail=f"回测完成: {payload.get('symbol') or ''} / {payload.get('strategy') or ''}",
            meta={"symbol": payload.get("symbol"), "strategy": payload.get("strategy")},
        )
        return ok_resource(
            resource=result,
            resource_key="backtest_result",
            enable_legacy_alias=legacy,
            metrics=result.get("metrics", {}),
        )

    @blueprint.post("/backtest")
    @login_required
    def backtest_legacy_shape():
        svc = runtime.require_strategy_service()
        payload = request.get_json(silent=True) or {}
        result = svc.backtest(
            symbol=payload.get("symbol", ""),
            strategy_name=payload.get("strategy", "MA"),
            start=payload.get("start") or payload.get("start_date", ""),
            end=payload.get("end") or payload.get("end_date", ""),
            initial_capital=parse_float_param(
                payload.get("initial_capital"),
                name="initial_capital",
                default=100000,
                min_value=0,
            ),
        )
        runtime.push_task(
            event="strategy_backtest_completed",
            task_name="inline.strategy_backtest",
            detail=f"回测完成: {payload.get('symbol') or ''} / {payload.get('strategy') or ''}",
            meta={"symbol": payload.get("symbol"), "strategy": payload.get("strategy")},
        )
        response_payload = {
            **(result.get("metrics") or result.get("summary", {})),
            "trades": result.get("trades", []),
            "stock_data": result.get("stock_data", {}),
            "strategy": result.get("strategy", payload.get("strategy", "MA")),
            "symbol": result.get("symbol", payload.get("symbol", "")),
            "period": result.get("period", {}),
        }
        return ok_resource(
            resource=response_payload,
            resource_key="backtest_result",
            enable_legacy_alias=legacy,
            trades=response_payload.get("trades", []),
        )

    @blueprint.post("/strategies/backtest/compare")
    @login_required
    def compare_backtests():
        svc = runtime.require_strategy_service()
        payload = request.get_json(silent=True) or {}
        strategies = payload.get("strategies") or payload.get("strategy_names") or []
        if isinstance(strategies, str):
            strategies = [s.strip() for s in strategies.split(",") if s.strip()]
        current = payload.get("strategy") or payload.get("strategy_name")
        if current and current not in strategies:
            strategies = [current, *strategies]
        if len(strategies) < 2:
            strategies = list(dict.fromkeys([current or "MA", "MA", "RSI", "MACD"]))[:4]

        symbol = payload.get("symbol", "")
        start = payload.get("start") or payload.get("start_date", "")
        end = payload.get("end") or payload.get("end_date", "")
        initial_capital = parse_float_param(
            payload.get("initial_capital"),
            name="initial_capital",
            default=100000,
            min_value=0,
        )

        rows: list[dict] = []
        for strategy_name in strategies[:5]:
            bt = svc.backtest(
                symbol=symbol,
                strategy_name=strategy_name,
                start=start,
                end=end,
                initial_capital=initial_capital,
            )
            if isinstance(bt, dict) and bt.get("error"):
                rows.append(
                    {
                        "strategy_name": strategy_name,
                        "status": "error",
                        "error": bt["error"],
                    }
                )
                continue
            metrics = bt.get("metrics") if isinstance(bt.get("metrics"), dict) else {}
            rows.append(
                {
                    "strategy_name": strategy_name,
                    "status": "ok",
                    "total_return": bt.get("total_return", metrics.get("total_return")),
                    "annual_return": bt.get("annual_return", metrics.get("annual_return")),
                    "sharpe": bt.get("sharpe_ratio", metrics.get("sharpe")),
                    "max_drawdown": bt.get("max_drawdown", metrics.get("max_drawdown")),
                    "win_rate": bt.get("win_rate", metrics.get("win_rate")),
                    "trade_count": bt.get("trade_count", metrics.get("trade_count")),
                }
            )

        ok_rows = [r for r in rows if r.get("status") == "ok"]
        winner = None
        if ok_rows:
            winner = max(
                ok_rows,
                key=lambda r: float(r.get("total_return") or 0.0),
            ).get("strategy_name")

        result = {
            "symbol": symbol,
            "start": start,
            "end": end,
            "initial_capital": initial_capital,
            "comparisons": rows,
            "winner": winner,
        }
        return ok_resource(
            resource=result,
            resource_key="compare_result",
            enable_legacy_alias=legacy,
        )
