"""Shared MLflow hook for strategy backtest results."""

from __future__ import annotations

from app.core.logger import get_logger
from app.facade.dto.backtest_facade_dto import BacktestResultDTO
from app.infrastructure.mlflow.registry import ModelRegistry

logger = get_logger(__name__)


def attach_mlflow_run_id(
    payload: BacktestResultDTO,
    *,
    symbol: str,
    strategy_name: str,
    start: str,
    end: str,
    initial_capital: float,
) -> dict[str, object]:
    """Log backtest metrics to MLflow when available; return serialized DTO with optional run id."""
    run_id: str | None = None
    model_name: str | None = None
    model_version: str | None = None
    try:
        metrics = payload.model_dump(
            include={"total_return", "sharpe", "max_drawdown", "win_rate"},
            exclude_none=True,
        )
        log_result = ModelRegistry.log_backtest(
            f"{strategy_name}-{symbol}",
            symbol=symbol,
            strategy_name=strategy_name,
            metrics=metrics,
            params={
                "start": start,
                "end": end,
                "initial_capital": initial_capital,
            },
        )
        if isinstance(log_result, dict):
            run_id = str(log_result.get("run_id") or "") or None
            model_name = (log_result.get("model_name") or None) and str(
                log_result["model_name"]
            )
            model_version = (log_result.get("model_version") or None) and str(
                log_result["model_version"]
            )
    except Exception:
        logger.warning("MLflow backtest log skipped", exc_info=True)
    if run_id:
        payload.mlflow_run_id = run_id
    if model_name:
        payload.mlflow_model_name = model_name
    if model_version:
        payload.mlflow_model_version = model_version
    return payload.model_dump()
