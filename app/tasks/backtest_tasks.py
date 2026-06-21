"""Celery tasks for strategy backtests."""

from __future__ import annotations

from typing import Any

from app.application.dto.market_data_dto import BacktestRequestDTO
from app.application.errors import ValidationError
from app.core.logger import get_logger
from app.facade.dto.backtest_facade_dto import BacktestResultDTO
from app.infrastructure.mlflow.backtest_log_hook import attach_mlflow_run_id

logger = get_logger(__name__)


def run_strategy_backtest(
    *,
    symbol: str,
    strategy_name: str,
    start: str,
    end: str,
    initial_capital: float = 100000.0,
) -> dict[str, Any]:
    """Run backtest synchronously (usable from Celery worker or inline)."""
    from app.bootstrap_components.service_wiring import get_registry

    strategy_service = get_registry().get_or_none("strategy_service")
    if strategy_service is None:
        raise ValidationError("Strategy service not configured")

    dto = BacktestRequestDTO(
        symbol=symbol,
        strategy_name=strategy_name,
        start=start,
        end=end,
        initial_capital=initial_capital,
    )
    result = strategy_service.backtest(
        symbol=dto.symbol,
        strategy_name=dto.strategy_name,
        start=dto.start,
        end=dto.end,
        initial_capital=dto.initial_capital,
    )
    if isinstance(result, dict) and result.get("error"):
        raise ValidationError(str(result["error"]))
    normalized = BacktestResultDTO.from_service(result)
    return attach_mlflow_run_id(
        normalized,
        symbol=dto.symbol,
        strategy_name=dto.strategy_name,
        start=dto.start,
        end=dto.end,
        initial_capital=dto.initial_capital,
    )


def submit_strategy_backtest(
    *,
    symbol: str,
    strategy_name: str,
    start: str,
    end: str,
    initial_capital: float = 100000.0,
) -> dict[str, Any]:
    """Submit async backtest when Celery is configured; else run inline."""
    payload = {
        "symbol": symbol,
        "strategy_name": strategy_name,
        "start": start,
        "end": end,
        "initial_capital": initial_capital,
    }
    if run_strategy_backtest_task is not None:
        async_result = run_strategy_backtest_task.delay(**payload)
        return {
            "status": "queued",
            "task_id": async_result.id,
            "mode": "async",
        }
    logger.info("Celery unavailable; running backtest synchronously")
    result = run_strategy_backtest(**payload)
    return {"status": "completed", "mode": "sync", "result": result}


from app.celery_app import celery as _celery

if _celery is not None:

    @_celery.task(name="app.tasks.backtest_tasks.run_strategy_backtest")
    def run_strategy_backtest_task(
        *,
        symbol: str,
        strategy_name: str,
        start: str,
        end: str,
        initial_capital: float = 100000.0,
    ) -> dict[str, Any]:
        return run_strategy_backtest(
            symbol=symbol,
            strategy_name=strategy_name,
            start=start,
            end=end,
            initial_capital=initial_capital,
        )

else:
    run_strategy_backtest_task = None  # type: ignore[misc, assignment]

__all__ = [
    "run_strategy_backtest",
    "run_strategy_backtest_task",
    "submit_strategy_backtest",
]
