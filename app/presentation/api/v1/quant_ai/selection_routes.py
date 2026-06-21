"""Long-term and selector stock-picking routes."""

from __future__ import annotations

from datetime import datetime

from flask import Blueprint, request
from flask_login import login_required

from app.presentation.api.common import ok_collection, ok_response, parse_market
from app.presentation.api.request_parsers import parse_int_param
from app.presentation.api.v1.quant_ai.runtime import QuantAiRuntime
from app.presentation.api.v1_context import ApiV1Context


def register_quant_ai_selection_routes(
    blueprint: Blueprint,
    ctx: ApiV1Context,
    *,
    runtime: QuantAiRuntime,
) -> None:
    _ = ctx
    legacy = runtime.legacy
    enable_qlib = runtime.enable_qlib

    @blueprint.post("/long-term-select")
    @login_required
    def long_term_select():
        payload = request.get_json(silent=True) or {}
        strategy = payload.get("strategy", "classic")
        market = parse_market(payload.get("market", "CN"))
        top_n = parse_int_param(payload.get("top_n"), name="top_n", default=20, min_value=1)
        data_source = payload.get("data_source", "legacy")
        model_id = str(payload.get("model_id") or "").strip() or None
        horizon = parse_int_param(payload.get("horizon_days"), name="horizon_days", default=20, min_value=5)
        result = runtime.require_selection_source_service().select_stocks(
            strategy=strategy,
            market=market,
            top_n=top_n,
            data_source=data_source,
            enable_qlib=enable_qlib,
            model_id=model_id,
            horizon_days=horizon,
        )
        runtime.push_task(
            event="long_term_select_completed",
            task_name="inline.long_term_select",
            detail=f"中长线选股完成: {market.value} / {strategy} / Top{top_n} (data_source={data_source})",
            meta={
                "market": market.value,
                "strategy": strategy,
                "top_n": top_n,
                "data_source": data_source,
            },
        )
        return ok_collection(
            items=result["candidates"],
            item_key="candidates",
            enable_legacy_alias=legacy,
            strategy=strategy,
            market=market.value,
            data_source=(result.get("sentiment_analysis") or {}).get("data_source", "legacy"),
        )

    @blueprint.get("/long-term-select")
    @login_required
    def long_term_select_get():
        return ok_response(
            data={"message": "Use POST to select stocks", "methods": ["POST"]},
            legacy_alias_key=None,
            enable_legacy_alias=legacy,
        )

    @blueprint.post("/long-term-report")
    @login_required
    def long_term_report():
        payload = request.get_json(silent=True) or {}
        stocks = payload.get("stocks", [])
        avg_score = round(sum(float(item.get("score", 0) or 0) for item in stocks) / len(stocks), 2) if stocks else 0
        report_payload = {
            "generate_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "summary": f"本次共筛选出 {len(stocks)} 只标的, 平均评分 {avg_score}.",
            "stock_count": len(stocks),
            "avg_score": avg_score,
            "stocks": stocks,
            "investment_advice": ["优先分批建仓", "结合趋势与仓位管理", "设置止损线"],
            "risk_notice": "本结果仅供研究与复盘使用, 不构成投资建议.",
        }
        runtime.push_task(
            event="long_term_report_generated",
            task_name="inline.long_term_report",
            detail=f"中长线选股报告已生成 (stocks={len(stocks)})",
            meta={"stock_count": len(stocks), "avg_score": avg_score},
        )
        return ok_response(data=report_payload, legacy_alias_key=None, enable_legacy_alias=legacy)

    @blueprint.get("/long-term-report")
    @login_required
    def long_term_report_get():
        return ok_response(
            data={"message": "Use POST to generate report", "methods": ["POST"]},
            legacy_alias_key=None,
            enable_legacy_alias=legacy,
        )

    @blueprint.route("/selector/run", methods=["GET", "POST"])
    @login_required
    def selector_run():
        payload = request.get_json(silent=True) or request.args.to_dict()
        selector_type = payload.get("type", "long")
        if selector_type == "short":
            strategy_name = "horizon:short"
        elif selector_type == "mid":
            strategy_name = "horizon:mid"
        else:
            strategy_name = "horizon:long"
        top_n = parse_int_param(payload.get("top_n"), name="top_n", default=20, min_value=1)
        market = parse_market(payload.get("market", "CN"))
        data_source = payload.get("data_source", "legacy")
        model_id = str(payload.get("model_id") or "").strip() or None
        horizon = parse_int_param(payload.get("horizon_days"), name="horizon_days", default=20, min_value=5)
        result = runtime.require_selection_source_service().select_stocks(
            strategy=strategy_name,
            market=market,
            top_n=top_n,
            data_source=data_source,
            enable_qlib=enable_qlib,
            model_id=model_id,
            horizon_days=horizon,
        )
        runtime.push_task(
            event="selector_run_completed",
            task_name="inline.selector_run",
            detail=f"选股完成: {market.value} / {selector_type} / Top{top_n} (data_source={data_source})",
            meta={
                "market": market.value,
                "selector_type": selector_type,
                "top_n": top_n,
                "data_source": data_source,
                "strategy": strategy_name,
            },
        )
        return ok_collection(
            items=result.get("candidates", []) if result else [],
            item_key="results",
            enable_legacy_alias=legacy,
            selector_type=selector_type,
            strategy=strategy_name,
            data_source=(result.get("sentiment_analysis") or {}).get("data_source", "legacy") if result else "legacy",
        )

    @blueprint.post("/selector/report")
    @login_required
    def selector_report():
        payload = request.get_json(silent=True) or {}
        stocks = payload.get("stocks", [])
        lines = ["选股报告", "==========", f"数量: {len(stocks)}"]
        for item in stocks[:20]:
            lines.append(f"{item.get('code', '')} {item.get('name', '')} 分数:{item.get('score', '-')}")
        report = "\n".join(lines)
        runtime.push_task(
            event="selector_report_generated",
            task_name="inline.selector_report",
            detail=f"选股报告已生成 (stocks={len(stocks)})",
            meta={"stock_count": len(stocks)},
        )
        return ok_response(data=report, legacy_alias_key=None, enable_legacy_alias=legacy)

    @blueprint.get("/selector/report")
    @login_required
    def selector_report_get():
        return ok_response(
            data={"message": "Use POST to generate report", "methods": ["POST"]},
            legacy_alias_key=None,
            enable_legacy_alias=legacy,
        )
