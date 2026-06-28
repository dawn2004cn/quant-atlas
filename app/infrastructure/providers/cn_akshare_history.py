from __future__ import annotations

"""A 股日 K 东财前复权（AkShare），作通达信/缓存失败时的行情兜底。"""


from datetime import date
from typing import Any

import pandas as pd

from ...core.logger import get_logger

logger = get_logger(__name__)


def _ymd_compact(d: str) -> str:
    s = (d or "").strip().replace("-", "")[:8]
    return s if len(s) == 8 and s.isdigit() else ""


def _ak_hist_to_bars(df: pd.DataFrame) -> list[dict[str, Any]]:
    if df is None or df.empty:
        return []
    cols = list(df.columns)
    date_c = next((c for c in cols if "日期" in str(c)), cols[0])
    open_c = next((c for c in cols if str(c) == "开盘" or "开盘" in str(c)), None)
    close_c = next((c for c in cols if str(c) == "收盘" or "收盘" in str(c)), None)
    high_c = next((c for c in cols if str(c) == "最高" or "最高" in str(c)), None)
    low_c = next((c for c in cols if str(c) == "最低" or "最低" in str(c)), None)
    vol_c = next((c for c in cols if "成交量" in str(c) or str(c) == "成交量"), None)
    amt_c = next((c for c in cols if "成交额" in str(c) or str(c) == "成交额"), None)
    if not all([open_c, close_c, high_c, low_c]):
        if len(cols) >= 6:
            open_c, close_c, high_c, low_c = cols[2], cols[3], cols[4], cols[5]
            vol_c = cols[6] if len(cols) > 6 else vol_c
            amt_c = cols[7] if len(cols) > 7 else amt_c
        else:
            return []
    out: list[dict[str, Any]] = []
    for _, row in df.iterrows():
        raw_d = row[date_c]
        if hasattr(raw_d, "strftime"):
            ds = raw_d.strftime("%Y-%m-%d")
        else:
            ds = str(raw_d)[:10]
        try:
            o, h, l_, c = float(row[open_c]), float(row[high_c]), float(row[low_c]), float(row[close_c])
            v = float(row[vol_c]) if vol_c is not None else 0.0
            a = float(row[amt_c]) if amt_c is not None and amt_c in df.columns else 0.0
        except (TypeError, ValueError, KeyError):
            continue
        out.append(
            {
                "date": ds,
                "open": o,
                "high": h,
                "low": l_,
                "close": c,
                "volume": v,
                "amount": a,
            },
        )
    out.sort(key=lambda x: x["date"])
    return out


def fetch_cn_daily_adjust(
    symbol_6: str,
    start_yyyy_mm_dd: str,
    end_yyyy_mm_dd: str,
    *,
    adjust: str = "qfq",
) -> tuple[list[dict[str, Any]], str]:
    """东财日 K；``adjust`` 为 ``qfq`` / ``hfq`` / ``none``（不复权）。"""
    code = "".join(c for c in str(symbol_6) if c.isdigit())[-6:].zfill(6)
    if len(code) != 6:
        return [], "invalid_code"
    s8 = _ymd_compact(start_yyyy_mm_dd) or "19900101"
    e8 = _ymd_compact(end_yyyy_mm_dd) or date.today().strftime("%Y%m%d")
    adj = (adjust or "none").strip().lower()
    if adj not in {"qfq", "hfq", "none", ""}:
        adj = "qfq"
    ak_adjust = "" if adj in {"none", ""} else adj
    try:
        import akshare as ak
    except ImportError:
        return [], "akshare_missing"
    try:
        df = ak.stock_zh_a_hist(
            symbol=code,
            period="daily",
            start_date=s8,
            end_date=e8,
            adjust=ak_adjust,
        )
    except Exception as exc:
        logger.warning("fetch_cn_daily_adjust akshare failed %s: %s", code, exc)
        return [], f"akshare_error:{exc!s}"
    bars = _ak_hist_to_bars(df)
    label = ak_adjust or "none"
    ev = f"AkShare stock_zh_a_hist {label} 区间={s8}~{e8} 条数={len(bars)}。"
    return bars, ev


def fetch_cn_daily_qfq(
    symbol_6: str,
    start_yyyy_mm_dd: str,
    end_yyyy_mm_dd: str,
) -> tuple[list[dict[str, Any]], str]:
    """东财日 K 前复权；``symbol_6`` 为 6 位沪深代码。"""
    return fetch_cn_daily_adjust(
        symbol_6,
        start_yyyy_mm_dd,
        end_yyyy_mm_dd,
        adjust="qfq",
    )


def fetch_cn_daily_hfq(
    symbol_6: str,
    start_yyyy_mm_dd: str,
    end_yyyy_mm_dd: str,
) -> tuple[list[dict[str, Any]], str]:
    """东财日 K 后复权（研究/委员会分析默认，避免前视偏差）。"""
    return fetch_cn_daily_adjust(
        symbol_6,
        start_yyyy_mm_dd,
        end_yyyy_mm_dd,
        adjust="hfq",
    )
