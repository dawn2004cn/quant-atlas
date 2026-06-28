from __future__ import annotations

"""Alpha Factory orchestration HTTP routes."""


import numpy as np
from flask import Blueprint, request
from flask_login import login_required

from app.application.errors import ValidationError
from app.core.logger import get_logger
from app.presentation.api.common import ok_response
from app.presentation.api.request_parsers import parse_bool_param
from app.presentation.api.v1_context import ApiV1Context

logger = get_logger(__name__)


def register_alpha_factory_routes(blueprint: Blueprint, ctx: ApiV1Context) -> None:
    legacy = ctx.enable_legacy_response_fields

    @blueprint.post("/alpha-factory/evolve")
    @login_required
    def alpha_factory_evolve():
        body = request.get_json(silent=True) or {}
        factor_id = body.get("factor_id")
        if not factor_id:
            raise ValidationError("factor_id_required")
        from app.modules.data.services.alpha_factory_orchestrator import get_orchestrator
        result = get_orchestrator().evolve_factor_targeted(factor_id)
        return ok_response(data=result, legacy_alias_key=None, enable_legacy_alias=legacy)

    @blueprint.post("/alpha-factory/experiment/submit")
    @login_required
    def alpha_factory_experiment_submit():
        body = request.get_json(silent=True) or {}
        from app.modules.data.services.alpha_factory_orchestrator import get_orchestrator
        formula = body.get("formula", "")
        data_scope = body.get("data_scope")
        save_to_vault = body.get("save_to_vault", False)
        result = get_orchestrator().submit_factor_experiment(
            formula=formula,
            data_scope=data_scope,
            save_to_vault=save_to_vault,
        )
        return ok_response(data=result, legacy_alias_key=None, enable_legacy_alias=legacy)

    @blueprint.post("/alpha-factory/experiment/analyze")
    @login_required
    def alpha_factory_experiment_analyze():
        body = request.get_json(silent=True) or {}
        from app.modules.data.services.alpha_factory_orchestrator import get_orchestrator
        experiment_id = body.get("experiment_id", "")
        backtest_result = body.get("backtest_result")
        result = get_orchestrator().analyze_experiment_result(
            experiment_id=experiment_id,
            backtest_result=backtest_result,
        )
        return ok_response(data=result, legacy_alias_key=None, enable_legacy_alias=legacy)

    @blueprint.get("/alpha-factory/lineage")
    @login_required
    def alpha_factory_lineage():
        from app.modules.data.services.alpha_factory_orchestrator import get_orchestrator
        limit = request.args.get("limit", 150, type=int)
        result = get_orchestrator().get_lineage_graph(limit=limit)
        return ok_response(data=result, legacy_alias_key=None, enable_legacy_alias=legacy)

    @blueprint.get("/alpha-factory/status")
    @login_required
    def alpha_factory_status():
        from app.modules.data.services.alpha_factory_orchestrator import get_orchestrator
        result = get_orchestrator().get_dashboard()
        return ok_response(data=result, legacy_alias_key=None, enable_legacy_alias=legacy)

    @blueprint.get("/alpha-factory/factors")
    @login_required
    def alpha_factory_factors():
        from app.domain.alpha.factor_vault import get_factor_vault
        vault = get_factor_vault()
        page = request.args.get("page", 1, type=int)
        limit = request.args.get("limit", 20, type=int)
        items = vault.list(page=page, limit=limit) if hasattr(vault, "list") else []
        return ok_response(data={"items": items, "total": len(items)}, legacy_alias_key=None, enable_legacy_alias=legacy)

    @blueprint.get("/alpha-factory/knowledge/alphas")
    @login_required
    def alpha_factory_knowledge():
        from app.domain.alpha.worldquant_alphas import ALPHA_EXAMPLES, ALPHA_OPERATORS, ALPHA_TEMPLATES
        return ok_response(data={"alphas": ALPHA_EXAMPLES[:50], "operators": ALPHA_OPERATORS, "templates": ALPHA_TEMPLATES}, legacy_alias_key=None, enable_legacy_alias=legacy)

    @blueprint.get("/alpha-factory/model/meta-learner")
    @login_required
    def alpha_factory_meta_learner():
        from app.domain.alpha.meta_learner import select_model
        symbols = request.args.get("symbols", "")
        pref = parse_bool_param(request.args.get("prefer_explainability", "false"), name="prefer_explainability")
        model = select_model(symbol=symbols, prefer_explainability=pref)
        return ok_response(data={"recommendation": str(model) if model else None}, legacy_alias_key=None, enable_legacy_alias=legacy)

    @blueprint.get("/alpha-factory/simulate")
    @login_required
    def alpha_factory_simulate():
        formula = (request.args.get("formula") or "").strip()
        symbol = (request.args.get("symbol") or "600519").strip()
        if not formula:
            raise ValidationError("formula_required")
        from datetime import date
        from datetime import timedelta as _td

        import pandas as pd

        from app.domain.enums import MarketCode
        end = date.today()
        start = end - _td(days=365)
        bars = ctx.market_service.get_history(symbol, MarketCode.CN, start=start.isoformat(), end=end.isoformat())
        if not bars:
            return ok_response(data={"series": [], "stats": {"mean": 0, "std": 0}, "error": "no_data", "symbol": symbol, "formula": formula, "meta": {"demo": False, "source": "no_data"}}, legacy_alias_key=None, enable_legacy_alias=legacy)
        df = pd.DataFrame(bars)
        for c in ["close", "open", "high", "low", "volume"]:
            if c in df.columns:
                df[c] = pd.to_numeric(df[c], errors="coerce").ffill()
        close = df["close"].values
        ret = np.diff(close) / close[:-1]
        ret = np.insert(ret, 0, 0)
        series = [{"date": str(r.get("date", ""))[:10], "value": round(float(v), 4)} for r, v in zip(bars, ret)]
        return ok_response(
            data={
                "formula": formula,
                "symbol": symbol,
                "series": series,
                "stats": {"mean": round(float(np.mean(ret)), 4), "std": round(float(np.std(ret)), 4)},
                "meta": {"demo": False, "source": "real_market_data", "bar_count": len(bars)},
            },
            legacy_alias_key=None,
            enable_legacy_alias=legacy,
        )

    @blueprint.get("/alpha-factory/validate")
    @login_required
    def alpha_factory_validate():
        from app.domain.alpha.alpha_parser import validate_alpha_expression
        formula = (request.args.get("formula") or "").strip()
        if not formula:
            raise ValidationError("formula is required")
        result = validate_alpha_expression(formula)
        return ok_response(data=result, legacy_alias_key=None, enable_legacy_alias=legacy)

    @blueprint.get("/alpha-factory/correlation")
    @login_required
    def alpha_factory_correlation():
        from app.domain.alpha.portfolio_correlation import get_correlation_analyzer
        analyzer = get_correlation_analyzer()
        result = analyzer.get_correlation_matrix()
        return ok_response(data=result, legacy_alias_key=None, enable_legacy_alias=legacy)

    @blueprint.get("/alpha-factory/online-learning")
    @login_required
    def alpha_factory_online_learning():
        return ok_response(data={"status": "not_configured", "mode": "online_learning_stub"}, legacy_alias_key=None, enable_legacy_alias=legacy)

    @blueprint.get("/alpha-factory/model-zoo")
    @login_required
    def alpha_factory_model_zoo():
        from app.domain.alpha.model_zoo import get_model_zoo
        market_cap = request.args.get("market_cap", "")
        zoo = get_model_zoo()
        models = zoo.list(market_cap=market_cap) if hasattr(zoo, "list") else []
        return ok_response(data={"models": models}, legacy_alias_key=None, enable_legacy_alias=legacy)

    @blueprint.get("/alpha-factory/paper-trading")
    @login_required
    def alpha_factory_paper_trading():
        from app.domain.alpha.paper_trading import get_paper_trading_scheduler
        scheduler = get_paper_trading_scheduler()
        return ok_response(data={"status": scheduler.get_queue_status()}, legacy_alias_key=None, enable_legacy_alias=legacy)

    @blueprint.post("/alpha-factory/paper-trading")
    @login_required
    def alpha_factory_submit_paper_trading():
        from app.domain.alpha.paper_trading import get_paper_trading_scheduler
        body = request.get_json(silent=True) or {}
        model_id = body.get("model_id")
        backtest_result = body.get("backtest_result")
        scheduler = get_paper_trading_scheduler()
        run_id = scheduler.submit_for_paper_trading(model_id, backtest_result)
        return ok_response(data={"run_id": run_id}, legacy_alias_key=None, enable_legacy_alias=legacy)

    @blueprint.get("/alpha-factory/weekly")
    @login_required
    def alpha_factory_weekly_meeting():
        from app.domain.alpha.weekly_meeting_scheduler import WeeklyMeetingScheduler
        s = WeeklyMeetingScheduler()
        return ok_response(data=s.get_status() if hasattr(s, "get_status") else {"enabled": False}, legacy_alias_key=None, enable_legacy_alias=legacy)

    @blueprint.post("/alpha-factory/weekly/enable")
    @login_required
    def alpha_factory_enable_weekly():
        body = request.get_json(silent=True) or {}
        enabled = body.get("enabled", True)
        return ok_response(data={"enabled": enabled}, legacy_alias_key=None, enable_legacy_alias=legacy)

    @blueprint.post("/alpha-factory/weekly/run")
    @login_required
    def alpha_factory_run_weekly():
        from app.domain.alpha.weekly_meeting_scheduler import WeeklyMeetingExecutor
        e = WeeklyMeetingExecutor()
        result = e.execute() if hasattr(e, "execute") else {"ok": True}
        return ok_response(data=result, legacy_alias_key=None, enable_legacy_alias=legacy)

    @blueprint.get("/alpha-factory/pipeline")
    @login_required
    def alpha_factory_pipeline():
        return ok_response(data={"status": "pipeline_placeholder"}, legacy_alias_key=None, enable_legacy_alias=legacy)

    @blueprint.post("/alpha-factory/pipeline")
    @login_required
    def alpha_factory_submit_pipeline():
        return ok_response(data={"ok": True, "message": "pipeline_placeholder"}, legacy_alias_key=None, enable_legacy_alias=legacy)

    @blueprint.get("/alpha-factory/search-strategy")
    @login_required
    def alpha_factory_search_strategy():
        return ok_response(data={"strategies": []}, legacy_alias_key=None, enable_legacy_alias=legacy)
