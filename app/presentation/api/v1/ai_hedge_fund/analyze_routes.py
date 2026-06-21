"""AI hedge fund analyze route."""

from __future__ import annotations

from flask import Blueprint, request

from app.application.errors import ValidationError
from app.integration.ai_hedge_fund.dto import HedgeFundAnalysisRequest
from app.presentation.api.common import ok_response
from app.presentation.api.v1.ai_hedge_fund.runtime import AiHedgeFundRuntime
from app.presentation.api.v1_context import ApiV1Context


def register_ai_hedge_fund_analyze_routes(
    blueprint: Blueprint,
    ctx: ApiV1Context,
    *,
    runtime: AiHedgeFundRuntime,
) -> None:
    _ = ctx

    @blueprint.route("/analyze", methods=["POST"])
    def analyze():
        """Run AI Hedge Fund multi-agent analysis."""
        data = request.get_json() or {}
        symbols = data.get("symbols", [])
        start_date = data.get("start_date", "20240101")
        end_date = data.get("end_date", "20250427")
        selected_agents = data.get("selected_agents")
        run_validation = data.get("run_validation", True)

        if not symbols:
            raise ValidationError("symbols_required")

        req = HedgeFundAnalysisRequest(
            symbols=symbols,
            start_date=start_date,
            end_date=end_date,
            selected_agents=selected_agents,
        )

        result = runtime.service.analyze(req, run_validation=run_validation)

        return ok_response(data={
            "symbols": result.symbols,
            "analysis_timestamp": result.analysis_timestamp.isoformat(),
            "agent_signals": [
                {
                    "agent_name": s.agent_name,
                    "agent_style": s.agent_style,
                    "signal": s.signal,
                    "confidence": s.confidence,
                    "reasoning": s.reasoning,
                }
                for s in result.agent_signals
            ],
            "aggregated_signal": result.aggregated_signal,
            "consensus_score": result.consensus_score,
            "validation_results": [
                {
                    "validation_type": v.validation_type,
                    "passed": v.passed,
                    "metrics": v.metrics,
                    "errors": v.errors,
                }
                for v in result.validation_results
            ],
            "validation_passed": result.validation_passed,
            "rd_agent_job_id": result.rd_agent_job_id,
            "qlib_backtest_result": result.qlib_backtest_result,
            "is_ready_for_trading": result.is_ready_for_trading,
            "summary": result.summary,
        })
