"""Minute-bar backtest engines for SRS D6 baseline / optimization.

Vectorized path is the default. Does **not** claim 10y-minute ≤10s until the
benchmark artifact says so. Uses close-to-close long/flat (no short).
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any, Literal

import numpy as np

from app.domain.trading.fee_schedule import get_fee_schedule

EngineMode = Literal["vectorized", "loop"]


@dataclass(frozen=True, slots=True)
class MinuteBacktestResult:
    n_bars: int
    n_trades: int
    final_equity: float
    total_return: float
    max_drawdown: float
    elapsed_s: float
    engine: EngineMode
    fee_schedule_id: str | None
    initial_capital: float

    def as_dict(self) -> dict[str, Any]:
        return {
            "n_bars": self.n_bars,
            "n_trades": self.n_trades,
            "final_equity": round(self.final_equity, 6),
            "total_return": round(self.total_return, 8),
            "max_drawdown": round(self.max_drawdown, 8),
            "elapsed_s": round(self.elapsed_s, 6),
            "engine": self.engine,
            "fee_schedule_id": self.fee_schedule_id,
            "initial_capital": self.initial_capital,
        }


def synthetic_minute_closes(n: int, *, seed: int = 7) -> np.ndarray:
    """Deterministic synthetic close series (not live market data)."""
    rng = np.random.default_rng(seed)
    steps = rng.normal(0.0, 0.0004, size=int(n))
    # mild drift + mean reversion noise
    closes = 100.0 * np.exp(np.cumsum(steps))
    return closes.astype(np.float64)


def square_wave_signal(n: int, *, period: int = 500) -> np.ndarray:
    """Alternate flat/long every ``period`` bars (0/1)."""
    t = np.arange(int(n), dtype=np.int32)
    return ((t // max(1, int(period))) % 2).astype(np.int8)


def _max_drawdown(equity: np.ndarray) -> float:
    if equity.size == 0:
        return 0.0
    peak = np.maximum.accumulate(equity)
    dd = (peak - equity) / np.where(peak <= 0, 1.0, peak)
    return float(np.max(dd)) if dd.size else 0.0


def _apply_trade_fees(
    *,
    equity_path: np.ndarray,
    sig: np.ndarray,
    fee_schedule_id: str | None,
) -> tuple[float, int]:
    prev = np.concatenate([[0], sig[:-1]])
    changed = sig != prev
    trade_idx = np.flatnonzero(changed)
    if trade_idx.size == 0:
        return 0.0, 0
    if not fee_schedule_id:
        return 0.0, int(trade_idx.size)
    schedule = get_fee_schedule(fee_schedule_id)
    fees = 0.0
    for i in trade_idx:
        eq = float(equity_path[int(i)]) if i < len(equity_path) else float(equity_path[-1])
        side = "buy" if int(sig[int(i)]) == 1 else "sell"
        fees += schedule.calculate(notional=max(eq, 0.0), side=side).total  # type: ignore[arg-type]
    return float(fees), int(trade_idx.size)


def run_minute_backtest(
    closes: np.ndarray | list[float],
    signal: np.ndarray | list[int],
    *,
    initial_capital: float = 1_000_000.0,
    fee_schedule_id: str | None = "cn_a_retail_v1",
    mode: EngineMode = "vectorized",
) -> MinuteBacktestResult:
    """Long/flat minute backtest. ``signal[t]=1`` means long into bar t+1."""
    px = np.asarray(closes, dtype=np.float64)
    sig = np.asarray(signal, dtype=np.int8)
    if px.ndim != 1 or sig.ndim != 1 or px.size != sig.size or px.size < 2:
        raise ValueError("closes_and_signal_length_mismatch")
    if mode == "loop":
        return _run_loop(px, sig, initial_capital=initial_capital, fee_schedule_id=fee_schedule_id)
    return _run_vectorized(px, sig, initial_capital=initial_capital, fee_schedule_id=fee_schedule_id)


def _run_vectorized(
    px: np.ndarray,
    sig: np.ndarray,
    *,
    initial_capital: float,
    fee_schedule_id: str | None,
) -> MinuteBacktestResult:
    t0 = time.perf_counter()
    ret = np.empty(px.size, dtype=np.float64)
    ret[0] = 0.0
    ret[1:] = px[1:] / px[:-1] - 1.0
    pos_held = np.empty(px.size, dtype=np.float64)
    pos_held[0] = 0.0
    pos_held[1:] = sig[:-1].astype(np.float64)
    strat_ret = pos_held * ret
    equity = initial_capital * np.cumprod(1.0 + strat_ret)
    fees, n_trades = _apply_trade_fees(equity_path=equity, sig=sig, fee_schedule_id=fee_schedule_id)
    final = float(equity[-1] - fees)
    elapsed = time.perf_counter() - t0
    return MinuteBacktestResult(
        n_bars=int(px.size),
        n_trades=n_trades,
        final_equity=final,
        total_return=(final / initial_capital - 1.0) if initial_capital else 0.0,
        max_drawdown=_max_drawdown(equity),
        elapsed_s=elapsed,
        engine="vectorized",
        fee_schedule_id=fee_schedule_id,
        initial_capital=initial_capital,
    )


def _run_loop(
    px: np.ndarray,
    sig: np.ndarray,
    *,
    initial_capital: float,
    fee_schedule_id: str | None,
) -> MinuteBacktestResult:
    t0 = time.perf_counter()
    schedule = get_fee_schedule(fee_schedule_id) if fee_schedule_id else None
    equity = float(initial_capital)
    peak = equity
    max_dd = 0.0
    pos = 0
    n_trades = 0
    for t in range(px.size):
        target = int(sig[t])
        if target != pos and schedule is not None:
            side = "buy" if target == 1 else "sell"
            equity -= schedule.calculate(notional=max(equity, 0.0), side=side).total  # type: ignore[arg-type]
            n_trades += 1
        elif target != pos:
            n_trades += 1
        if t > 0 and pos == 1:
            equity *= float(px[t] / px[t - 1])
        pos = target
        if equity > peak:
            peak = equity
        if peak > 0:
            max_dd = max(max_dd, (peak - equity) / peak)
    elapsed = time.perf_counter() - t0
    return MinuteBacktestResult(
        n_bars=int(px.size),
        n_trades=n_trades,
        final_equity=equity,
        total_return=(equity / initial_capital - 1.0) if initial_capital else 0.0,
        max_drawdown=float(max_dd),
        elapsed_s=elapsed,
        engine="loop",
        fee_schedule_id=fee_schedule_id,
        initial_capital=initial_capital,
    )


# ~10y A-share minutes: 250d × 240min × 10 ≈ 600_000
TEN_YEAR_MINUTE_BARS = 600_000

__all__ = [
    "TEN_YEAR_MINUTE_BARS",
    "MinuteBacktestResult",
    "run_minute_backtest",
    "square_wave_signal",
    "synthetic_minute_closes",
]
