from __future__ import annotations
from typing import Any
from app.domain.strategies.base import BaseStrategy, StrategyResult, StrategySignal

class RiskAnalysisStrategy(BaseStrategy):
    """
    Concrete implementation of risk analysis logic.
    Decoupled from Service and Persistence.
    """

    def setup(self, config: dict[str, Any]) -> None:
        self.fib_levels = config.get("fib_levels", [0.236, 0.382, 0.5, 0.618, 0.786])
        self.sma_window = config.get("sma_window", 20)

    def analyze(self, data: dict[str, Any]) -> StrategyResult:
        price = float(data.get("close", data.get("price", 0)))
        high = float(data.get("high", price))
        low = float(data.get("low", price))
        code = data.get("code", data.get("symbol", ""))

        range_val = high - low
        supports = []
        resistances = []

        for fib in self.fib_levels:
            level = low + range_val * fib
            if level < price:
                supports.append(round(level, 2))
            else:
                resistances.append(round(level, 2))

        signals: list[StrategySignal] = []
        if supports:
            signals.append(StrategySignal(
                code=code, direction="long", strength=min(len(supports) / 5, 1.0),
                stop_loss=min(supports), reason=f"support_at_{min(supports)}",
            ))

        return StrategyResult(
            signals=signals,
            metrics={
                "support": sorted(set(supports))[-3:],
                "resistance": sorted(set(resistances))[:3],
            },
        )

    def on_bar(self, bar: dict[str, Any]) -> dict[str, Any]:
        result = self.analyze(bar)
        return result.metrics
