from __future__ import annotations
"""A-share (China mainland) backtest engine.

Market rules:
  - T+1: cannot sell shares bought today
  - No short selling for retail investors
  - Price limits: ±10% main board, ±20% ChiNext/STAR, ±5% ST
  - Minimum lot: 100 shares (odd lots can only be sold, not bought)
  - Commission: ¥5 minimum, 0.025% bilateral
  - Stamp tax: 0.025% sell-side only (2023-08-28+)
  - Transfer fee: 0.002% bilateral
"""


import pandas as pd

from backtest.engines.base import BaseEngine
from backtest.engines.cn_market_rules import (
    a_share_t1_blocks_sell,
    cn_apply_tick_slippage,
    cn_stamp_tax_rate_for_date,
)


import logging
logger = logging.getLogger(__name__)


def _listing_status(code: str, date_str: str) -> str:
    """Check listing status from cn_stock_basics."""
    try:
        from app.infrastructure.providers.cn_backtest_rules import listing_status_for_code
        return listing_status_for_code(code, date_str)
    except Exception:
        return "U"


class ChinaAEngine(BaseEngine):
    """A-share market engine.

    Config keys:
      - commission_rate: default 0.00025 (万2.5)
      - commission_min: default 5.0 (RMB)
      - stamp_tax: default 0.00025 (万2.5, sell-only, post-2023-08)
      - transfer_fee: default 0.00002 (万2 bilateral)
      - slippage: default 0.001
    """

    def __init__(self, config: dict):
        config = {**config, "leverage": 1.0}  # A-shares: no leverage
        super().__init__(config)
        self.commission_rate: float = config.get("commission_rate", 0.00025)
        self.commission_min: float = config.get("commission_min", 5.0)
        self.stamp_tax: float = config.get("stamp_tax", 0.00025)
        self.transfer_fee: float = config.get("transfer_fee", 0.00002)
        self.slippage_rate: float = config.get("slippage", 0.001)

    def can_execute(self, symbol: str, direction: int, bar: pd.Series) -> bool:
        """A-share execution rules.

        Args:
            symbol: Stock code (e.g. 000001.SZ).
            direction: 1 (buy), -1 (short — always blocked), 0 (sell/close).
            bar: Current bar (needs 'close', 'pre_close' or 'pct_chg').

        Returns:
            True if the trade is allowed.
        """
        # 0. Listing status: block trades on delisted stocks
        raw_code = symbol.replace(".SZ", "").replace(".SH", "").replace(".BJ", "")
        date_str = str(bar.name)[:10] if hasattr(bar, "name") and bar.name else ""
        status = _listing_status(raw_code, date_str)
        if status == "D":
            return False

        # 1. No short selling
        if direction == -1:
            return False

        # 2. T+1: cannot sell on the entry bar (trading-session rule)
        if direction == 0 and a_share_t1_blocks_sell(self, symbol):
            return False

        # 3. Price limits
        pct_chg = _calc_pct_change(bar)
        if pct_chg is not None:
            limit = _price_limit(symbol)
            if direction == 1 and pct_chg >= limit - 0.001:
                return False  # limit-up: can't buy
            if direction == 0 and pct_chg <= -limit + 0.001:
                return False  # limit-down: can't sell

        return True

    def round_size(self, raw_size: float, price: float) -> float:
        """Round down to 100-share lots."""
        return max(int(raw_size / 100) * 100, 0)

    def calc_commission(self, size: float, price: float, direction: int, is_open: bool) -> float:
        """A-share fee structure: commission + stamp tax (sell) + transfer fee."""
        notional = size * price
        # Commission: 万2.5, min ¥5
        comm = max(notional * self.commission_rate, self.commission_min)
        # Transfer fee: 万0.1 bilateral
        comm += notional * self.transfer_fee
        # Stamp tax: 万5 sell-only, rate depends on trade date for long backtests
        if not is_open:
            trade_date = None
            trade_ts = getattr(self, "_trade_ts", None)
            if trade_ts is not None and hasattr(trade_ts, "date"):
                trade_date = trade_ts.date()
            stamp_rate = cn_stamp_tax_rate_for_date(trade_date, self.stamp_tax)
            comm += notional * stamp_rate
        return comm

    def apply_slippage(self, price: float, direction: int) -> float:
        """A-share slippage: proportional model floored at one price tick."""
        return cn_apply_tick_slippage(price, direction, self.slippage_rate)


# ── Helpers ──


def _bar_date(bar: pd.Series):
    """Extract date from bar, handling various column names."""
    for col in ("trade_date", "date"):
        if col in bar.index:
            val = bar[col]
            if hasattr(val, "date"):
                return val.date()
            try:
                return pd.Timestamp(val).date()
            except Exception as e:
                logger.warning("china_a.py._bar_date: %s", e)
    # Fall back to bar name (index timestamp)
    if hasattr(bar, "name") and hasattr(bar.name, "date"):
        return bar.name.date()
    return None


def _calc_pct_change(bar: pd.Series):
    """Calculate price change percentage from bar data."""
    if "pct_chg" in bar.index:
        val = bar["pct_chg"]
        if pd.notna(val):
            return float(val) / 100.0  # tushare pct_chg is in percentage points

    close = bar.get("close")
    pre_close = bar.get("pre_close")
    if close is not None and pre_close is not None and pre_close > 0:
        return (float(close) - float(pre_close)) / float(pre_close)
    return None


def _price_limit(symbol: str) -> float:
    """Determine price limit based on board.

    Args:
        symbol: Stock code (e.g. 300001.SZ, 688001.SH, 000001.SZ).

    Returns:
        Limit as fraction (0.10, 0.20, or 0.05).
    """
    code = symbol.split(".")[0] if "." in symbol else symbol
    # ChiNext (300xxx) / STAR (688xxx): ±20%
    if code.startswith("300") or code.startswith("688"):
        return 0.20
    # ST stocks: ±5% (heuristic: can't fully detect from code alone)
    # Beijing exchange (8xxxxx): ±30% — simplified to 0.30
    if code.startswith("8") and len(code) == 6:
        return 0.30
    # Main board: ±10%
    return 0.10
