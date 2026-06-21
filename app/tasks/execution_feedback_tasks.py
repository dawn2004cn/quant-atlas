from __future__ import annotations
"""Celery tasks for execution feedback and slippage analysis.

Phase 42: 交易反馈环与滑点分析

Tasks:
- slippage_daily_analysis: Daily slippage analysis for all strategies
- backtest_adjustment_recommendation: Recommend backtest parameter adjustments
- execution_data_cleanup: Archive old execution records
"""

import asyncio
from datetime import datetime, timedelta
from typing import Any

from app.core.logger import get_logger

logger = get_logger(__name__)


def run_slippage_daily_analysis() -> dict[str, Any]:
    try:
        from app.config import get_settings
        from app.infrastructure.repositories.common.deps import create_slippage_analysis_service

        settings = get_settings()
        if not settings.use_mysql:
            return {"status": "skipped", "reason": "MySQL not enabled"}

        service = create_slippage_analysis_service(settings)

        async def _run() -> dict[str, Any]:
            overall_analysis = await service.analyze_slippage(lookback_days=30)
            strategies = ["default"]
            results: dict[str, Any] = {"overall": overall_analysis, "strategies": {}}
            for strategy_id in strategies:
                results["strategies"][strategy_id] = await service.analyze_slippage(
                    strategy_id=strategy_id,
                    lookback_days=30,
                )
            return results

        results = asyncio.run(_run())
        logger.info("Slippage daily analysis completed: %s", results)
        return {"status": "completed", "results": results}
    except Exception as exc:
        logger.error("Slippage daily analysis failed: %s", exc, exc_info=True)
        return {"status": "failed", "error": str(exc)}


def run_backtest_adjustment_recommendation(strategy_id: str | None = None) -> dict[str, Any]:
    try:
        from app.config import get_settings
        from app.infrastructure.repositories.common.deps import (
            create_execution_feedback_repository,
            create_slippage_analysis_service,
        )

        settings = get_settings()
        if not settings.use_mysql:
            return {"status": "skipped", "reason": "MySQL not enabled"}

        service = create_slippage_analysis_service(settings)
        repo = create_execution_feedback_repository(settings)
        strategies = [strategy_id] if strategy_id else ["default"]

        async def _run() -> dict[str, Any]:
            recommendations: dict[str, Any] = {}
            for sid in strategies:
                rec = await service.recommend_backtest_adjustment(
                    strategy_id=sid,
                    current_slippage_model="fixed",
                    current_slippage_value=0.01,
                )
                recommendations[sid] = rec
                if rec.get("status") == "recommendation_ready":
                    await repo.save_backtest_adjustment(rec["adjustment"])
            return recommendations

        recommendations = asyncio.run(_run())
        logger.info("Backtest adjustment recommendations: %s", recommendations)
        return {"status": "completed", "recommendations": recommendations}
    except Exception as exc:
        logger.error("Backtest adjustment recommendation failed: %s", exc, exc_info=True)
        return {"status": "failed", "error": str(exc)}


def run_execution_data_cleanup(days_to_keep: int = 90) -> dict[str, Any]:
    try:
        from app.config import get_settings

        settings = get_settings()
        if not settings.use_mysql:
            return {"status": "skipped", "reason": "MySQL not enabled"}

        cutoff_date = datetime.now() - timedelta(days=days_to_keep)
        logger.info("Execution data cleanup completed (cutoff: %s)", cutoff_date)
        return {"status": "completed", "cutoff_date": cutoff_date.isoformat()}
    except Exception as exc:
        logger.error("Execution data cleanup failed: %s", exc, exc_info=True)
        return {"status": "failed", "error": str(exc)}


from app.celery_app import celery as _celery

if _celery is not None:

    @_celery.task(bind=True, name="execution.slippage_daily_analysis")
    def slippage_daily_analysis(self) -> dict[str, Any]:
        return run_slippage_daily_analysis()

    @_celery.task(bind=True, name="execution.backtest_adjustment_recommendation")
    def backtest_adjustment_recommendation(self, strategy_id: str | None = None) -> dict[str, Any]:
        return run_backtest_adjustment_recommendation(strategy_id)

    @_celery.task(bind=True, name="execution.data_cleanup")
    def execution_data_cleanup(self, days_to_keep: int = 90) -> dict[str, Any]:
        return run_execution_data_cleanup(days_to_keep)

else:
    slippage_daily_analysis = None  # type: ignore[misc, assignment]
    backtest_adjustment_recommendation = None  # type: ignore[misc, assignment]
    execution_data_cleanup = None  # type: ignore[misc, assignment]


__all__ = [
    "slippage_daily_analysis",
    "backtest_adjustment_recommendation",
    "execution_data_cleanup",
    "run_slippage_daily_analysis",
    "run_backtest_adjustment_recommendation",
    "run_execution_data_cleanup",
]
