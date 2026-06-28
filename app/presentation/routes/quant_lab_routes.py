from __future__ import annotations

"""量化实验室 API：``/api/factor/list``、``/api/model/predict``、``/api/backtest/compare``。"""


from flask import Blueprint, jsonify, request
from flask_login import login_required

from ...application.errors import ValidationError
from ...application.services.factor.factor_catalog_service import FactorCatalogService
from ...application.services.qlib.backtest_compare_service import BacktestCompareService
from ...application.services.research.model_predict_lab_service import ModelPredictLabService
from ...domain.enums import MarketCode
from ..api.request_parsers import parse_float_param, parse_int_param
from ..api.response_builders import build_success_payload, with_legacy_aliases


def _parse_market_lab(raw: str | None) -> MarketCode:
    try:
        return MarketCode((raw or "CN").strip().upper())
    except ValueError:
        return MarketCode.CN


def create_quant_lab_blueprint(
    *,
    factor_catalog_service: FactorCatalogService,
    model_predict_service: ModelPredictLabService,
    backtest_compare_service: BacktestCompareService,
    enable_rd_agent: bool = False,
    enable_qlib: bool = False,
    enable_legacy_response_fields: bool = False,
) -> Blueprint:
    bp = Blueprint("quant_lab_api", __name__, url_prefix="/api")

    def _wrap(data: dict, meta: dict | None = None):
        payload = build_success_payload(data=data, meta=meta)
        return jsonify(with_legacy_aliases(payload, alias_key=None, enabled=enable_legacy_response_fields))

    @bp.get("/factor/list")
    @login_required
    def factor_list():
        if not enable_rd_agent:
            return _wrap(
                {"factors": [], "runs_index": [], "total": 0},
                meta={"warning": "ENABLE_RD_AGENT 未开启，返回空列表"},
            )
        run_id = (request.args.get("run_id") or "").strip() or None
        limit_runs = parse_int_param(request.args.get("limit_runs"), name="limit_runs", default=30, min_value=1)
        limit_factors = parse_int_param(
            request.args.get("limit_factors"), name="limit_factors", default=800, min_value=1
        )
        out = factor_catalog_service.list_factors(
            run_id=run_id, limit_runs=limit_runs, limit_factors=limit_factors
        )
        return _wrap(out)

    @bp.get("/factor/autopublish")
    @login_required
    def factor_autopublish_tail():
        """RD 注册后追加的 ``autopublish.jsonl`` 尾部记录（便于外部分析/对账）。"""
        if not enable_rd_agent:
            return _wrap({"records": [], "total": 0, "path": ""}, meta={"warning": "ENABLE_RD_AGENT 未开启"})
        lim = parse_int_param(request.args.get("limit"), name="limit", default=120, min_value=1)
        lim = min(lim, 500)
        out = factor_catalog_service.list_autopublish_tail(limit=lim)
        return _wrap(out)

    @bp.get("/factor/monitor")
    @login_required
    def factor_monitor():
        """因子健康摘要：弱 IC（|lag1 IC| 低于阈值）计数与警报列表（需 ENABLE_RD_AGENT）。"""
        if not enable_rd_agent:
            return _wrap(
                {
                    "ic_warn_threshold": 0.05,
                    "factor_task_rows": 0,
                    "factors_with_ic_decay": 0,
                    "weak_ic_lag1_count": 0,
                    "mean_abs_ic_lag1": None,
                    "alerts": [],
                    "runs_index": [],
                },
                meta={"warning": "ENABLE_RD_AGENT 未开启，返回空摘要"},
            )
        ic_thr = parse_float_param(
            request.args.get("ic_warn"),
            name="ic_warn",
            default=0.05,
            min_value=0.0,
        )
        limit_runs = parse_int_param(request.args.get("limit_runs"), name="limit_runs", default=30, min_value=1)
        limit_factors = parse_int_param(
            request.args.get("limit_factors"), name="limit_factors", default=500, min_value=1
        )
        ap_raw = request.args.get("autopublish_tail")
        ap_kw: dict = {}
        if ap_raw is not None and str(ap_raw).strip() != "":
            ap_kw["autopublish_tail"] = min(
                parse_int_param(ap_raw, name="autopublish_tail", default=0, min_value=0),
                500,
            )
        out = factor_catalog_service.monitor_summary(
            ic_warn_threshold=float(ic_thr),
            limit_runs=limit_runs,
            limit_factors=limit_factors,
            **ap_kw,
        )
        return _wrap(out, meta={"ic_warn_threshold": float(ic_thr)})

    @bp.post("/model/predict")
    @login_required
    def model_predict():
        body = request.get_json(silent=True) or {}
        if not isinstance(body, dict):
            raise ValidationError("JSON object required")
        raw_syms = body.get("symbols") or body.get("codes") or []
        if isinstance(raw_syms, str):
            raw_syms = [raw_syms]
        symbols = [str(s).strip() for s in raw_syms if str(s).strip()]
        if not symbols:
            raise ValidationError("symbols 必填（非空数组）")
        if len(symbols) > 80:
            raise ValidationError("symbols 最多 80 只")
        market = _parse_market_lab(body.get("market"))
        model_id = str(body.get("model_id") or body.get("model") or "lgbm").strip()
        horizon = parse_int_param(body.get("horizon_days"), name="horizon_days", default=20, min_value=5)
        out = model_predict_service.predict_rank(
            symbols=symbols, market=market, model_id=model_id, horizon_days=horizon
        )
        return _wrap(out, meta={"market": market.value})

    @bp.post("/backtest/compare")
    @login_required
    def backtest_compare():
        body = request.get_json(silent=True) or {}
        if not isinstance(body, dict):
            raise ValidationError("JSON object required")
        strategy_id = str(body.get("strategy_id") or body.get("strategy") or "").strip()
        symbol = str(body.get("symbol") or "").strip()
        start = str(body.get("start") or body.get("start_date") or "").strip()
        end = str(body.get("end") or body.get("end_date") or "").strip()
        if not strategy_id:
            raise ValidationError("strategy_id 必填")
        if not symbol:
            raise ValidationError("symbol 必填")
        if not start or not end:
            raise ValidationError("start / end 必填 (YYYY-MM-DD)")
        capital = parse_float_param(
            body.get("initial_capital"),
            name="initial_capital",
            default=100_000,
            min_value=1000,
        )
        out = backtest_compare_service.compare(
            strategy_id=strategy_id,
            symbol=symbol,
            start=start,
            end=end,
            initial_capital=capital,
            enable_qlib=enable_qlib,
        )
        return _wrap(out, meta={"enable_qlib": enable_qlib})

    return bp
