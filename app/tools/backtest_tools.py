from __future__ import annotations

"""Backtest Tools - 回测相关工具."""


from typing import Any

from langchain_core.tools import tool
from pydantic import BaseModel, ConfigDict, Field

from ..core.logger import get_logger

logger = get_logger(__name__)


class BacktestToolResult(BaseModel):
    model_config = ConfigDict(extra="ignore")

    ticker: str
    ok: bool = True
    error: str | None = None
    metrics: dict[str, Any] = Field(default_factory=dict)
    trades: list[dict[str, Any]] = Field(default_factory=list)
    evidence: str = ""
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)


class BatchBacktestToolResult(BaseModel):
    model_config = ConfigDict(extra="ignore")

    total: int = 0
    success: int = 0
    failed: int = 0
    results: list[dict[str, Any]] = Field(default_factory=list)
    avg_return: float | None = None
    evidence: str = ""
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)


class QlibBacktestToolResult(BaseModel):
    model_config = ConfigDict(extra="ignore")

    strategy: str
    ok: bool = True
    error: str | None = None
    results: dict[str, Any] = Field(default_factory=dict)
    evidence: str = ""
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)


@tool
def run_backtest(
    strategy: str,
    ticker: str,
    start_date: str | None = None,
    end_date: str | None = None,
    initial_capital: float = 100000.0,
    commission_rate: float = 0.0003,
) -> BacktestToolResult:
    """执行单策略、单标的回测."""
    from datetime import datetime, timedelta

    from ..application.services.tool_facade_service import get_tool_facade_service

    if not start_date:
        start_date = (datetime.now() - timedelta(days=365)).strftime("%Y-%m-%d")
    if not end_date:
        end_date = datetime.now().strftime("%Y-%m-%d")

    try:
        service = get_tool_facade_service()
        result = service.run_backtest(
            strategy=strategy,
            ticker=ticker,
            start_date=start_date,
            end_date=end_date,
            initial_capital=initial_capital,
            commission_rate=commission_rate,
        )
        return BacktestToolResult(
            ticker=ticker,
            metrics=result.get("metrics", {}),
            trades=result.get("trades", []),
            evidence=f"Backtest completed for {ticker}",
            confidence=0.8,
        )
    except Exception as e:
        logger.error(f"run_backtest failed: {e}")
        return BacktestToolResult(
            ticker=ticker,
            ok=False,
            error=str(e),
            confidence=0.3,
        )


@tool
def batch_backtest_selection(
    selection_result: list[dict[str, Any]],
    strategy: str = "dual_thrust",
    start_date: str = "",
    end_date: str = "",
    initial_capital: float = 100000.0,
) -> BatchBacktestToolResult:
    """对选股结果进行批量回测."""
    from datetime import datetime, timedelta

    if not start_date:
        start_date = (datetime.now() - timedelta(days=365)).strftime("%Y-%m-%d")
    if not end_date:
        end_date = datetime.now().strftime("%Y-%m-%d")

    success_results = []
    failed_results = []
    total_return = 0.0
    success_count = 0

    from ..application.services.tool_facade_service import get_tool_facade_service

    service = get_tool_facade_service()

    for item in selection_result:
        ticker = item.get("ticker") or item.get("symbol")
        if not ticker:
            continue

        try:
            result = service.run_backtest(
                strategy=strategy,
                ticker=ticker,
                start_date=start_date,
                end_date=end_date,
                initial_capital=initial_capital,
            )
            ret = result.get("metrics", {}).get("total_return", 0.0)
            success_results.append({"ticker": ticker, "return": ret})
            total_return += ret
            success_count += 1
        except Exception as e:
            failed_results.append({"ticker": ticker, "error": str(e)})

    avg_return = total_return / success_count if success_count > 0 else 0.0

    return BatchBacktestToolResult(
        total=len(selection_result),
        success=success_count,
        failed=len(failed_results),
        results=success_results + failed_results,
        avg_return=avg_return,
        evidence=f"Batch backtest: {success_count}/{len(selection_result)} succeeded",
        confidence=0.7,
    )


@tool
def run_qlib_unified_backtest(
    strategy: str,
    start_date: str | None = None,
    end_date: str | None = None,
    task_id: str = "",
    model_name: str = "lgb",
    label_name: str = "Ref(-1) - Ref(-2)",
) -> QlibBacktestToolResult:
    """运行Qlib统一回测."""
    from datetime import datetime, timedelta

    from ..application.services.qlib.qlib_service import create_default_qlib_service

    if not start_date:
        start_date = (datetime.now() - timedelta(days=365)).strftime("%Y-%m-%d")
    if not end_date:
        end_date = datetime.now().strftime("%Y-%m-%d")

    try:
        service = create_default_qlib_service()
        result = service.run_unified_backtest(
            strategy=strategy,
            start_date=start_date,
            end_date=end_date,
            task_id=task_id,
            model_name=model_name,
            label_name=label_name,
        )
        return QlibBacktestToolResult(
            strategy=strategy,
            results=result,
            evidence=f"Qlib backtest completed for {strategy}",
            confidence=0.8,
        )
    except Exception as e:
        logger.error(f"run_qlib_unified_backtest failed: {e}")
        return QlibBacktestToolResult(
            strategy=strategy,
            ok=False,
            error=str(e),
            confidence=0.3,
        )
