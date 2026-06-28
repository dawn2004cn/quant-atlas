from __future__ import annotations

"""High-Fidelity Execution Engine - Slippage, Impact & Consistency.

This module implements from strategy_plan.md:
- SlippageModel: Volume-based impact cost modeling
- TickSimulator: Tick-level order matching
- ConsistencyAudit: Compare live vs backtest prices

Usage:
    executor = HighFidelityExecutor()
    real_price = executor.apply_slippage(order_price, volume, liquidity)
    audit_result = executor.audit_consistency(live_prices, backtest_prices)
"""


from dataclasses import dataclass
from datetime import datetime
from typing import Any

from app.core.logger import get_logger

logger = get_logger(__name__)


@dataclass
class ExecutionResult:
    """Result of order execution with costs."""
    order_id: str
    requested_price: float
    executed_price: float
    slippage: float
    slippage_pct: float
    impact_cost: float
    total_cost: float
    timestamp: datetime


@dataclass
class ConsistencyAuditResult:
    """Result of consistency audit between live and backtest."""
    symbol: str
    avg_deviation: float
    max_deviation: float
    deviation_count: int
    total_trades: int
    audit_passed: bool
    recommendations: list[str]


class SlippageModel:
    """Volume-based slippage and impact cost model."""

    def __init__(
        self,
        base_slippage: float = 0.0005,
        impact_coefficient: float = 0.1,
    ):
        self._base_slippage = base_slippage
        self._impact_coefficient = impact_coefficient

    def calculate_slippage(
        self,
        order_price: float,
        order_volume: float,
        market_volume: float,
        volatility: float = 0.2,
    ) -> float:
        """Calculate slippage based on order size relative to market."""
        if market_volume <= 0:
            return self._base_slippage * order_price

        participation_rate = order_volume / market_volume

        if participation_rate > 0.1:
            impact = self._impact_coefficient * (participation_rate ** 2) * volatility
        else:
            impact = self._base_slippage * (1 + participation_rate * 5)

        return impact * order_price

    def calculate_impact_cost(
        self,
        order_price: float,
        order_value: float,
        daily_volume: float,
    ) -> float:
        """Calculate market impact cost."""
        if daily_volume <= 0:
            return 0.0

        turnover_ratio = order_value / daily_volume

        if turnover_ratio < 0.01:
            return 0.0
        elif turnover_ratio < 0.05:
            return order_price * turnover_ratio * 0.1
        else:
            impact_factor = 0.1 + (turnover_ratio - 0.05) * 2
            return order_price * turnover_ratio * impact_factor


class TickSimulator:
    """Tick-level order matching simulator."""

    def __init__(self):
        self._order_book: list[dict[str, Any]] = []

    def simulate_order(
        self,
        order_side: str,
        order_price: float,
        order_volume: float,
        market_data: dict[str, Any],
    ) -> dict[str, Any]:
        """Simulate order execution at tick level."""
        bids = market_data.get("bids", [])
        asks = market_data.get("asks", [])

        if order_side == "buy":
            levels = asks
        else:
            levels = bids

        filled_volume = 0
        total_cost = 0
        remaining_volume = order_volume

        for level_price, level_volume in levels:
            if remaining_volume <= 0:
                break

            fill_vol = min(remaining_volume, level_volume)
            filled_volume += fill_vol
            total_cost += fill_vol * level_price
            remaining_volume -= fill_vol

        if filled_volume > 0:
            avg_price = total_cost / filled_volume
        else:
            avg_price = order_price

        return {
            "executed_price": avg_price,
            "filled_volume": filled_volume,
            "remaining_volume": remaining_volume,
            "fill_rate": filled_volume / order_volume if order_volume > 0 else 0,
        }


class ConsistencyAuditor:
    """Audit consistency between live trading and backtest."""

    def __init__(self, deviation_threshold: float = 0.01):
        self._threshold = deviation_threshold
        self._trade_history: list[dict[str, Any]] = []

    def record_trade(
        self,
        symbol: str,
        live_price: float,
        backtest_price: float,
        timestamp: datetime,
    ) -> None:
        """Record a trade for comparison."""
        self._trade_history.append({
            "symbol": symbol,
            "live_price": live_price,
            "backtest_price": backtest_price,
            "timestamp": timestamp,
            "deviation": abs(live_price - backtest_price) / backtest_price if backtest_price > 0 else 0,
        })

    def audit_symbol(self, symbol: str) -> ConsistencyAuditResult:
        """Audit consistency for a specific symbol."""
        symbol_trades = [t for t in self._trade_history if t["symbol"] == symbol]

        if not symbol_trades:
            return ConsistencyAuditResult(
                symbol=symbol,
                avg_deviation=0.0,
                max_deviation=0.0,
                deviation_count=0,
                total_trades=0,
                audit_passed=True,
                recommendations=["No trades to audit"],
            )

        deviations = [t["deviation"] for t in symbol_trades]
        avg_deviation = sum(deviations) / len(deviations)
        max_deviation = max(deviations)
        deviation_count = sum(1 for d in deviations if d > self._threshold)

        audit_passed = avg_deviation < self._threshold

        recommendations = []
        if avg_deviation > 0.02:
            recommendations.append("回测与实盘偏差过大，建议重新校准滑点模型")
        if deviation_count > len(symbol_trades) * 0.3:
            recommendations.append("超过30%的交易存在显著偏差，建议检查数据质量")

        return ConsistencyAuditResult(
            symbol=symbol,
            avg_deviation=avg_deviation,
            max_deviation=max_deviation,
            deviation_count=deviation_count,
            total_trades=len(symbol_trades),
            audit_passed=audit_passed,
            recommendations=recommendations,
        )


class HighFidelityExecutor:
    """Complete high-fidelity execution engine."""

    def __init__(
        self,
        slippage_model: SlippageModel | None = None,
        tick_simulator: TickSimulator | None = None,
        auditor: ConsistencyAuditor | None = None,
    ):
        self._slippage = slippage_model or SlippageModel()
        self._tick_sim = tick_simulator or TickSimulator()
        self._auditor = auditor or ConsistencyAuditor()

    def apply_slippage(
        self,
        order_price: float,
        order_volume: float,
        market_volume: float,
        volatility: float = 0.2,
    ) -> float:
        """Apply slippage to order price."""
        slippage = self._slippage.calculate_slippage(
            order_price,
            order_volume,
            market_volume,
            volatility,
        )
        return order_price * (1 + slippage / order_price)

    def execute_with_costs(
        self,
        order_side: str,
        order_price: float,
        order_volume: float,
        market_data: dict[str, Any],
    ) -> ExecutionResult:
        """Execute order with full cost modeling."""
        tick_result = self._tick_sim.simulate_order(
            order_side,
            order_price,
            order_volume,
            market_data,
        )

        executed_price = tick_result["executed_price"]
        slippage = abs(executed_price - order_price)
        slippage_pct = slippage / order_price if order_price > 0 else 0

        impact_cost = self._slippage.calculate_impact_cost(
            executed_price,
            order_volume * executed_price,
            market_data.get("daily_volume", 0),
        )

        return ExecutionResult(
            order_id=f"ord_{datetime.now().timestamp()}",
            requested_price=order_price,
            executed_price=executed_price,
            slippage=slippage,
            slippage_pct=slippage_pct,
            impact_cost=impact_cost,
            total_cost=slippage + impact_cost,
            timestamp=datetime.now(),
        )

    def record_for_audit(
        self,
        symbol: str,
        live_price: float,
        backtest_price: float,
    ) -> None:
        """Record trade for consistency audit."""
        self._auditor.record_trade(symbol, live_price, backtest_price, datetime.now())

    def audit_symbol(self, symbol: str) -> ConsistencyAuditResult:
        """Audit symbol for consistency."""
        return self._auditor.audit_symbol(symbol)


_global_executor: HighFidelityExecutor | None = None


def get_high_fidelity_executor() -> HighFidelityExecutor:
    """Get singleton high-fidelity executor."""
    global _global_executor
    if _global_executor is None:
        _global_executor = HighFidelityExecutor()
    return _global_executor


def reset_high_fidelity_executor() -> None:
    """Reset singleton (for testing)."""
    global _global_executor
    _global_executor = None
