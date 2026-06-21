"""Re-export all test factories for convenient imports."""

from .domain import (
    build_backtest_result,
    build_evidence,
    build_market_bar,
    build_research_state,
    build_trade_order,
)

__all__ = [
    "build_backtest_result",
    "build_evidence",
    "build_market_bar",
    "build_research_state",
    "build_trade_order",
]
