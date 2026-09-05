from __future__ import annotations

"""Shared preview/hyperopt signals (Freqtrade / VectorBT style, no lookahead)."""

from collections.abc import Mapping, Sequence
from typing import Any


def strategy_returns(
    prices: Sequence[float],
    params: Mapping[str, Any] | None = None,
    strategy: str = "auto",
) -> list[float]:
    """Return next-bar strategy returns aligned to ``prices`` (first bar is 0)."""
    close = [float(p) for p in prices]
    bh = _pct_change(close)
    params = dict(params or {})
    tid = _resolve_strategy(strategy, params)

    if tid == "trend_following_basic":
        fast = max(1, int(params.get("fast_ma", 20)))
        slow = max(fast + 1, int(params.get("slow_ma", 60)))
        pos = _gt(_rolling_mean(close, fast), _rolling_mean(close, slow))
        return _apply_position(bh, pos)

    if tid == "mean_reversion_rsi":
        period = max(2, int(params.get("rsi_period", 14)))
        oversold = float(params.get("oversold", 30))
        overbought = float(params.get("overbought", 70))
        rsi = _rsi(close, period)
        pos = [0.0] * len(close)
        for i, value in enumerate(rsi):
            if value is None:
                continue
            if value < oversold:
                pos[i] = 1.0
            elif value > overbought:
                pos[i] = 0.0
        return _apply_position(bh, pos)

    if tid == "factor_momentum_alpha":
        lookback = max(1, int(params.get("lookback_period") or params.get("lookback") or params.get("period") or 5))
        mom = _pct_change(close, lookback)
        pos = [1.0 if x is not None and x > 0 else 0.0 for x in mom]
        return _apply_position(bh, pos)

    return [0.0 if x is None else x for x in bh]


def _resolve_strategy(strategy: str, params: Mapping[str, Any]) -> str:
    tid = (strategy or "auto").strip().lower()
    if tid not in {"", "auto"}:
        return tid
    if "fast_ma" in params or "slow_ma" in params:
        return "trend_following_basic"
    if "rsi_period" in params:
        return "mean_reversion_rsi"
    if "lookback_period" in params or "lookback" in params or "period" in params:
        return "factor_momentum_alpha"
    return "buy_hold"


def _pct_change(close: list[float], lookback: int = 1) -> list[float | None]:
    out: list[float | None] = [None] * len(close)
    for i in range(lookback, len(close)):
        prev = close[i - lookback]
        out[i] = (close[i] / prev - 1.0) if prev else 0.0
    return out


def _rolling_mean(xs: list[float], window: int) -> list[float | None]:
    out: list[float | None] = [None] * len(xs)
    if window <= 0:
        return out
    total = 0.0
    for i, val in enumerate(xs):
        total += val
        if i >= window:
            total -= xs[i - window]
        if i >= window - 1:
            out[i] = total / window
    return out


def _gt(left: list[float | None], right: list[float | None]) -> list[float]:
    pos: list[float] = []
    for a, b in zip(left, right):
        pos.append(1.0 if a is not None and b is not None and a > b else 0.0)
    return pos


def _apply_position(returns: list[float | None], position: list[float]) -> list[float]:
    lagged = [0.0, *position[:-1]]
    out: list[float] = []
    for ret, pos in zip(returns, lagged):
        out.append(0.0 if ret is None else pos * ret)
    return out


def _rsi(close: list[float], period: int) -> list[float | None]:
    out: list[float | None] = [None] * len(close)
    if period < 1 or len(close) < period + 1:
        return out
    gains = [0.0]
    losses = [0.0]
    for i in range(1, len(close)):
        delta = close[i] - close[i - 1]
        gains.append(delta if delta > 0 else 0.0)
        losses.append(-delta if delta < 0 else 0.0)
    gain_ma = _rolling_mean(gains, period)
    loss_ma = _rolling_mean(losses, period)
    for i, (g, loss) in enumerate(zip(gain_ma, loss_ma)):
        if g is None or loss is None:
            continue
        if loss == 0:
            out[i] = 100.0 if g > 0 else 50.0
            continue
        rs = g / loss
        out[i] = 100.0 - (100.0 / (1.0 + rs))
    return out
