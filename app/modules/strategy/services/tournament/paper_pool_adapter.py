"""Adapt StrategyTournamentService promotions to PaperTradingScheduler."""

from __future__ import annotations

from typing import Any

from app.core.logger import get_logger
from app.domain.alpha.paper_trading import PaperTradingScheduler, get_paper_trading_scheduler

logger = get_logger(__name__)


class PaperTradingPoolAdapter:
    """PaperPoolPort implementation backed by domain PaperTradingScheduler."""

    def __init__(self, *, scheduler: PaperTradingScheduler | None = None) -> None:
        self._scheduler = scheduler or get_paper_trading_scheduler()

    def promote(
        self,
        strategy_id: str,
        *,
        reason: str,
        metrics: dict[str, Any] | None = None,
    ) -> None:
        metrics = dict(metrics or {})
        backtest_result: dict[str, Any] = {
            "source": "strategy_tournament",
            "reason": reason,
            "total_return": float(metrics.get("total_return") or 0.0),
            "sharpe": float(metrics.get("sharpe") or 0.0),
            "max_drawdown": float(metrics.get("max_drawdown") or 0.0),
        }
        if metrics.get("win_rate") is not None:
            backtest_result["win_rate"] = float(metrics["win_rate"])
        if metrics.get("sample_start"):
            backtest_result["sample_start"] = str(metrics["sample_start"])
        if metrics.get("sample_end"):
            backtest_result["sample_end"] = str(metrics["sample_end"])
        for key, value in metrics.items():
            if key not in backtest_result:
                backtest_result[key] = value
        run_id = self._scheduler.submit_for_paper_trading(strategy_id, backtest_result)
        logger.info(
            "paper_pool promote strategy=%s run_id=%s sharpe=%s mdd=%s",
            strategy_id,
            run_id,
            backtest_result.get("sharpe"),
            backtest_result.get("max_drawdown"),
        )

    def reject(self, strategy_id: str, *, reason: str) -> None:
        logger.info("paper_pool reject strategy=%s reason=%s", strategy_id, reason)
