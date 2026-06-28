from __future__ import annotations
"""Shared A-share market rule helpers for backtest engines."""

from datetime import date
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from backtest.engines.base import BaseEngine

# 印花税调整节点（卖出单边）
_STAMP_TAX_2023_08 = date(2023, 8, 28)  # 0.1% -> 0.05%
_STAMP_TAX_2024_10 = date(2024, 10, 1)  # 0.05% -> 0.025%（政策落地近似日）


def cn_stamp_tax_rate_for_date(trade_date: date | None, fallback: float) -> float:
    """Return sell-side stamp tax rate for a trade date (historical schedule)."""
    if trade_date is None:
        return fallback
    if trade_date < _STAMP_TAX_2023_08:
        return 0.001
    if trade_date < _STAMP_TAX_2024_10:
        return 0.0005
    return fallback if fallback > 0 else 0.00025


def a_share_t1_blocks_sell(engine: BaseEngine, symbol: str) -> bool:
    """Return True when retail T+1 forbids selling (same trading bar as entry).

    Uses ``entry_bar_idx`` from the bar loop instead of calendar dates so
    suspended names do not unlock sells early across non-trading days.
    """
    pos = engine.positions.get(symbol)
    if pos is None:
        return False
    return engine._bar_idx <= pos.entry_bar_idx


def cn_price_tick_size(price: float) -> float:
    """Minimum price tick for A-share stocks (main board default 0.01 CNY)."""
    if price < 1.0:
        return 0.001
    return 0.01


def cn_apply_tick_slippage(price: float, direction: int, slippage_rate: float) -> float:
    """Apply adverse slippage with at least one exchange tick.

    Args:
        price: Reference price before slippage.
        direction: 1 buy / cover, -1 sell / short.
        slippage_rate: Proportional slippage (e.g. 0.001 = 10 bps).
    """
    tick = cn_price_tick_size(price)
    adverse = max(price * slippage_rate, tick)
    slipped = price + direction * adverse
    if tick >= 0.01:
        return float(round(round(slipped / tick) * tick, 2))
    return round(slipped, 3)
