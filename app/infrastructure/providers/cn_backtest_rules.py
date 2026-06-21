"""A-share daily-bar trade constraints for backtests."""

from __future__ import annotations

import re

import numpy as np
import pandas as pd

from app.domain.shared.symbol_normalizer import SymbolNormalizer


def cn_limit_threshold(symbol: str) -> float:
    """Price limit fraction by board (main 10%, ChiNext/STAR 20%, BJ 30%)."""
    code = SymbolNormalizer.normalize_code(symbol or "")
    if code.startswith(("300", "688")):
        return 0.20
    if code.startswith("8") and len(code) == 6:
        return 0.30
    return 0.10


def is_cn_symbol(symbol: str) -> bool:
    if not symbol:
        return False
    raw = str(symbol).strip().lower()
    if raw.startswith(("sh", "sz", "bj")):
        return True
    code = SymbolNormalizer.normalize_code(raw)
    return bool(re.fullmatch(r"\d{6}", code))


def listing_status_for_code(code: str, date_str: str | None = None) -> str:
    """Return listing status for an A-share code on a given date.

    Reads from ``cn_stock_basics.delist_date`` if available.
    Returns ``"L"`` (listed), ``"D"`` (delisted), or ``"U"`` (unknown).

    Use this in backtest engines to filter out delisted stocks on each bar.
    """
    if not code or not date_str:
        return "U"
    try:
        from app.core.db import get_session
        from app.infrastructure.database.models.market import CNStockBasic
        session = get_session()
        row = session.query(CNStockBasic).filter(CNStockBasic.symbol == code).first()
        if row is None:
            return "U"
        if row.listing_status == "D":
            delist = row.delist_date or "9999-12-31"
            if date_str >= delist:
                return "D"
        return "L"
    except Exception:
        return "U"


def can_trade_cn_bar(
    df: pd.DataFrame,
    bar_index: int,
    *,
    side: str,
    limit_thr: float | None = None,
) -> tuple[bool, str]:
    """Approximate halt / one-word-board / limit-up-down on daily bars."""
    if bar_index <= 0 or bar_index >= len(df):
        return False, "index_out_of_range"
    row = df.iloc[bar_index]
    prev = df.iloc[bar_index - 1]
    try:
        vol = float(row.get("Volume", row.get("volume", 0)))
    except (TypeError, ValueError):
        vol = 0.0
    if not np.isfinite(vol) or vol <= 0:
        return False, "HALT_OR_NO_VOLUME"
    try:
        o = float(row.get("Open", row.get("open", 0)))
        h = float(row.get("High", row.get("high", 0)))
        low = float(row.get("Low", row.get("low", 0)))
        close = float(row.get("Close", row.get("close", 0)))
        prev_close = float(prev.get("Close", prev.get("close", 0)))
    except (TypeError, ValueError):
        return False, "BAD_OHLC"
    if not all(np.isfinite(x) for x in (o, h, low, close, prev_close)) or prev_close <= 0:
        return False, "BAD_OHLC"
    if abs(h - low) < 1e-12:
        return False, "ONE_WORD_BOARD"
    thr = float(limit_thr if limit_thr is not None else 0.095)
    up = prev_close * (1.0 + thr)
    dn = prev_close * (1.0 - thr)
    eps = prev_close * 0.0005
    side_u = (side or "").strip().upper()
    if side_u == "BUY" and close >= (up - eps):
        return False, "LIMIT_UP"
    if side_u == "SELL" and close <= (dn + eps):
        return False, "LIMIT_DOWN"
    return True, "OK"


def can_trade_cn_on_date(
    df: pd.DataFrame,
    dt: object,
    *,
    side: str,
    limit_thr: float | None = None,
    symbol: str | None = None,
) -> tuple[bool, str]:
    """Resolve bar index by date then apply ``can_trade_cn_bar``."""
    if dt not in df.index:
        return True, "OK"
    idx = int(df.index.get_loc(dt))
    if isinstance(idx, slice):
        idx = idx.start or 0
    thr = limit_thr
    if thr is None and symbol:
        thr = cn_limit_threshold(symbol)
    return can_trade_cn_bar(df, idx, side=side, limit_thr=thr)
