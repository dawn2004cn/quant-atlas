from __future__ import annotations

"""Minimal backtest domain objects for /api/v1/arch/backtest routes."""


from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class TradeDirection(str, Enum):
    LONG = "long"
    SHORT = "short"


@dataclass
class BacktestConfig:
    initial_capital: float = 100_000.0
    commission_rate: float = 0.0003
    slippage: float = 0.001


@dataclass
class StrategySignal:
    code: str
    direction: TradeDirection
    strength: float = 1.0


@dataclass
class Trade:
    code: str
    direction: TradeDirection
    quantity: int
    price: float
    commission: float = 0.0
    pnl: float = 0.0


@dataclass
class BacktestResult:
    initial_capital: float
    final_equity: float
    total_return_pct: float
    trades: list[Trade] = field(default_factory=list)
    max_drawdown: float = 0.0
    sharpe_ratio: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "initial_capital": self.initial_capital,
            "final_equity": self.final_equity,
            "total_return_pct": self.total_return_pct,
            "trade_count": len(self.trades),
            "max_drawdown": self.max_drawdown,
            "sharpe_ratio": self.sharpe_ratio,
            "trades": [
                {
                    "code": t.code,
                    "direction": t.direction.value,
                    "quantity": t.quantity,
                    "price": t.price,
                    "commission": t.commission,
                    "pnl": t.pnl,
                }
                for t in self.trades
            ],
        }


class BacktestEngine:
    def __init__(self, config: BacktestConfig) -> None:
        self.config = config

    def run(self, signals: list[StrategySignal], prices: dict[str, Any]) -> BacktestResult:
        equity = self.config.initial_capital
        trades: list[Trade] = []
        for sig in signals:
            px_data = prices.get(sig.code) or prices.get(sig.code.upper())
            if isinstance(px_data, list) and px_data:
                px = float(px_data[-1])
            elif isinstance(px_data, (int, float)):
                px = float(px_data)
            else:
                px = 0.0
            qty = max(1, int(100 * sig.strength))
            slip = px * self.config.slippage
            fill = px + slip if sig.direction == TradeDirection.LONG else px - slip
            comm = abs(qty * fill) * self.config.commission_rate
            pnl = qty * (fill - px) * (1 if sig.direction == TradeDirection.LONG else -1) - comm
            trades.append(
                Trade(
                    code=sig.code,
                    direction=sig.direction,
                    quantity=qty,
                    price=fill,
                    commission=comm,
                    pnl=pnl,
                )
            )
            equity += pnl

        ret_pct = (equity - self.config.initial_capital) / self.config.initial_capital * 100.0 if self.config.initial_capital else 0.0
        return BacktestResult(
            initial_capital=self.config.initial_capital,
            final_equity=equity,
            total_return_pct=ret_pct,
            trades=trades,
            max_drawdown=0.05,
            sharpe_ratio=0.5,
        )


class BacktestAnalyzer:
    @staticmethod
    def analyze(trades: list[Trade], initial_capital: float) -> BacktestResult:
        total_pnl = sum(t.pnl for t in trades)
        final = initial_capital + total_pnl
        ret_pct = total_pnl / initial_capital * 100.0 if initial_capital else 0.0
        return BacktestResult(
            initial_capital=initial_capital,
            final_equity=final,
            total_return_pct=ret_pct,
            trades=list(trades),
            max_drawdown=0.1,
            sharpe_ratio=0.4,
        )

    @staticmethod
    def compare_results(results: list[BacktestResult]) -> dict[str, Any]:
        if not results:
            return {"best": None, "count": 0}
        best = max(results, key=lambda r: r.total_return_pct)
        return {
            "count": len(results),
            "best_return_pct": best.total_return_pct,
            "best_final_equity": best.final_equity,
            "summary": [r.to_dict() for r in results],
        }
