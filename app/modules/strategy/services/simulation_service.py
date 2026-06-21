"""High-Fidelity Simulation — HFT LOB simulator, walk-forward validation, Monte Carlo stress test."""

from __future__ import annotations

import json
import math
import random
import statistics
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.core.logger import get_logger

logger = get_logger(__name__)


@dataclass
class LimitOrderBook:
    """Simulated limit order book."""
    symbol: str
    bids: list[dict] = field(default_factory=list)  # [{price, volume, order_id}]
    asks: list[dict] = field(default_factory=list)
    spread: float = 0.0
    mid_price: float = 0.0
    last_trade_price: float = 0.0
    timestamp: str = ""


@dataclass
class MarketImpactResult:
    """Market impact estimate for an order."""
    symbol: str
    order_quantity: int
    side: str  # buy / sell
    arrival_price: float
    execution_price: float
    impact_bps: float  # basis points
    slippage_bps: float
    liquidity_score: float  # 0..1


@dataclass
class WalkForwardResult:
    """Walk-forward validation result."""
    strategy_id: str
    in_sample_sharpe: float
    out_of_sample_sharpe: float
    decay_rate: float  # how fast alpha decays OOS
    robust: bool  # True if OOS sharpe > 0.5 * IS sharpe


@dataclass
class MonteCarloResult:
    """Monte Carlo stress test result."""
    strategy_id: str
    iterations: int
    max_drawdowns: list[float]
    p95_max_drawdown: float
    p99_max_drawdown: float
    bankruptcy_probability: float  # P(max_drawdown > 50%)
    sharpe_distribution: dict[str, float]  # mean, std, p5, p95


class HftSimulatorService:
    """High-fidelity LOB simulator with market impact calculation."""

    def simulate_lob(self, symbol: str, base_price: float, depth: int = 10,
                     volatility: float = 0.002) -> LimitOrderBook:
        """Simulate a limit order book around a base price."""
        bids = []
        asks = []
        for i in range(depth):
            bid_price = base_price * (1 - (i + 1) * volatility * random.uniform(0.5, 1.5))
            ask_price = base_price * (1 + (i + 1) * volatility * random.uniform(0.5, 1.5))
            bid_vol = int(random.uniform(1000, 100000))
            ask_vol = int(random.uniform(1000, 100000))
            bids.append({"price": round(bid_price, 2), "volume": bid_vol, "order_id": f"b.{uuid.uuid4().hex[:6]}"})
            asks.append({"price": round(ask_price, 2), "volume": ask_vol, "order_id": f"a.{uuid.uuid4().hex[:6]}"})

        best_bid = max(b["price"] for b in bids)
        best_ask = min(a["price"] for a in asks)

        return LimitOrderBook(
            symbol=symbol,
            bids=bids,
            asks=asks,
            spread=round(best_ask - best_bid, 4),
            mid_price=round((best_bid + best_ask) / 2, 4),
            last_trade_price=round(base_price, 2),
            timestamp=datetime.now(timezone.utc).isoformat(),
        )

    def estimate_market_impact(self, symbol: str, order_quantity: int, side: str,
                               lob: LimitOrderBook) -> MarketImpactResult:
        """Estimate market impact of an order using LOB depth."""
        levels = lob.asks if side == "buy" else lob.bids
        arrival_price = lob.mid_price

        remaining = order_quantity
        total_cost = 0.0
        filled = 0

        for level in levels:
            if remaining <= 0:
                break
            fill = min(remaining, level["volume"])
            total_cost += fill * level["price"]
            remaining -= fill
            filled += fill

        if filled == 0:
            return MarketImpactResult(
                symbol=symbol, order_quantity=order_quantity, side=side,
                arrival_price=arrival_price, execution_price=arrival_price,
                impact_bps=0, slippage_bps=0, liquidity_score=0,
            )

        exec_price = total_cost / filled
        impact_bps = abs(exec_price - arrival_price) / arrival_price * 10000
        slippage_bps = impact_bps * random.uniform(0.8, 1.2)
        liquidity_score = min(1.0, filled / order_quantity)

        return MarketImpactResult(
            symbol=symbol,
            order_quantity=order_quantity,
            side=side,
            arrival_price=arrival_price,
            execution_price=round(exec_price, 4),
            impact_bps=round(impact_bps, 2),
            slippage_bps=round(slippage_bps, 2),
            liquidity_score=round(liquidity_score, 4),
        )


class WalkForwardService:
    """Walk-forward optimization and out-of-sample validation."""

    def validate(self, strategy_id: str, returns: list[float], window_size: int = 252,
                 step_size: int = 63) -> WalkForwardResult:
        """Run walk-forward validation on a return series."""
        in_sample_sharpes = []
        out_of_sample_sharpes = []

        for i in range(0, len(returns) - window_size - step_size, step_size):
            is_returns = returns[i:i + window_size]
            oos_returns = returns[i + window_size:i + window_size + step_size]

            if len(is_returns) < 10 or len(oos_returns) < 5:
                continue

            is_sharpe = self._compute_sharpe(is_returns)
            oos_sharpe = self._compute_sharpe(oos_returns)
            in_sample_sharpes.append(is_sharpe)
            out_of_sample_sharpes.append(oos_sharpe)

        if not in_sample_sharpes:
            return WalkForwardResult(strategy_id=strategy_id, in_sample_sharpe=0,
                                     out_of_sample_sharpe=0, decay_rate=1, robust=False)

        avg_is = statistics.mean(in_sample_sharpes)
        avg_oos = statistics.mean(out_of_sample_sharpes)
        decay = (avg_is - avg_oos) / max(abs(avg_is), 0.01) if avg_is != 0 else 1

        return WalkForwardResult(
            strategy_id=strategy_id,
            in_sample_sharpe=round(avg_is, 4),
            out_of_sample_sharpe=round(avg_oos, 4),
            decay_rate=round(decay, 4),
            robust=avg_oos > avg_is * 0.5,
        )

    def _compute_sharpe(self, returns: list[float], rf: float = 0.0) -> float:
        if len(returns) < 2:
            return 0.0
        mean_ret = statistics.mean(returns)
        std_ret = statistics.stdev(returns)
        if std_ret == 0:
            return 0.0
        return (mean_ret - rf) / std_ret * math.sqrt(252)


class MonteCarloService:
    """Monte Carlo stress testing for strategy robustness."""

    def stress_test(self, strategy_id: str, historical_returns: list[float],
                    iterations: int = 10000, confidence: float = 0.95) -> MonteCarloResult:
        """Run Monte Carlo simulation to estimate tail risk."""
        if len(historical_returns) < 10:
            return MonteCarloResult(
                strategy_id=strategy_id, iterations=0, max_drawdowns=[],
                p95_max_drawdown=0, p99_max_drawdown=0,
                bankruptcy_probability=0, sharpe_distribution={},
            )

        mean_ret = statistics.mean(historical_returns)
        std_ret = statistics.stdev(historical_returns)
        n = len(historical_returns)

        max_drawdowns = []
        sharpes = []

        for _ in range(iterations):
            # Simulate one path
            simulated = [random.gauss(mean_ret, std_ret) for _ in range(n)]
            # Compute max drawdown
            peak = simulated[0]
            mdd = 0.0
            for r in simulated:
                if r > peak:
                    peak = r
                dd = (peak - r) / peak if peak > 0 else 0
                mdd = max(mdd, dd)
            max_drawdowns.append(mdd)

            # Compute sharpe
            sim_mean = statistics.mean(simulated)
            sim_std = statistics.stdev(simulated)
            if sim_std > 0:
                sharpes.append((sim_mean - 0) / sim_std * math.sqrt(252))

        max_drawdowns.sort()
        sharpes.sort()

        p95_idx = int(iterations * 0.95)
        p99_idx = int(iterations * 0.99)
        bankrupt = sum(1 for dd in max_drawdowns if dd > 0.5) / iterations

        return MonteCarloResult(
            strategy_id=strategy_id,
            iterations=iterations,
            max_drawdowns=max_drawdowns[:100],  # keep top 100 for viz
            p95_max_drawdown=round(max_drawdowns[p95_idx], 4),
            p99_max_drawdown=round(max_drawdowns[p99_idx], 4),
            bankruptcy_probability=round(bankrupt, 6),
            sharpe_distribution={
                "mean": round(statistics.mean(sharpes), 4) if sharpes else 0,
                "std": round(statistics.stdev(sharpes), 4) if len(sharpes) > 1 else 0,
                "p5": round(sharpes[int(iterations * 0.05)], 4) if sharpes else 0,
                "p95": round(sharpes[p95_idx], 4) if sharpes else 0,
            },
        )
