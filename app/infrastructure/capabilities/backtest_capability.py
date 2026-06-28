from __future__ import annotations

"""Backtest execution capability."""


from datetime import date, timedelta
from typing import Any

from app.domain.capabilities.base import BaseCapability
from app.domain.enums import MarketCode
from app.infrastructure.capabilities.registry import capability


def _safe_initial_capital(raw: object, default: float = 100_000.0) -> float:
    try:
        v = float(raw) if raw is not None else default
    except (TypeError, ValueError):
        return default
    return default if v <= 0 else min(v, 1e12)


@capability("run_backtest")
class BacktestCapability(BaseCapability):
    """Run a single backtest for a given strategy & symbol."""

    capability_name = "run_backtest"

    def __init__(self, **services: Any) -> None:
        self._strategy_service = services.get("strategy_service")

    def execute(
        self,
        *,
        strategy_name: str,
        ticker: str,
        market: MarketCode,
        params: dict[str, Any] | None = None,
    ) -> tuple[dict[str, Any], str]:
        if not self._strategy_service:
            return (
                {"ok": False, "error": "Strategy service not initialized"},
                "strategy service not initialized",
            )

        p = params or {}
        end = str(p.get("end") or date.today().isoformat())
        start = str(p.get("start") or (date.today() - timedelta(days=365)).isoformat())
        capital = _safe_initial_capital(p.get("initial_capital", 100_000.0))
        note = (
            f"回测引擎: StrategyApplicationService.backtest; "
            f"策略={strategy_name}; 标的={ticker}; 区间={start}~{end}; 初始资金={capital}."
        )
        try:
            raw = self._strategy_service.backtest(
                symbol=ticker,
                strategy_name=strategy_name,
                start=start,
                end=end,
                initial_capital=capital,
            )
        except Exception as exc:
            return {"ok": False, "error": str(exc)}, f"{note} 执行失败: {exc!s}."
        return {**raw, "ok": True}, f"{note} 成功生成 metrics/trades。"
