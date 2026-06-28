from __future__ import annotations
"""通达信本地 lday（未除权）与东财前复权日 K 合并，供 Qlib CSV 与缓存。"""


from datetime import date, timedelta
from pathlib import Path
from typing import Any

import pandas as pd

from ..mappers.symbol_normalizer import SymbolNormalizer
from ..providers.cn_akshare_history import fetch_cn_daily_qfq
from ..tdx_local.lday_reader import read_lday_file
from ..tdx_local.paths import TdxLocalPaths, resolve_tdx_root

# 与 MarketDataAccess._period_to_days 对齐
_PERIOD_DAYS: dict[str, int] = {
    "5d": 5,
    "1m": 30,
    "3m": 91,
    "6m": 182,
    "1y": 365,
    "2y": 730,
    "5y": 1825,
    "max": 3650,
}


def period_to_date_bounds(period: str) -> tuple[str, str]:
    p = (period or "2y").strip().lower()
    days = _PERIOD_DAYS.get(p, 730)
    end = date.today()
    start = end - timedelta(days=days)
    return start.isoformat(), end.isoformat()


def load_cn_lday_bars(symbol: str, tdx_root: Path | None) -> list[dict[str, Any]]:
    raw = str(tdx_root.resolve()) if tdx_root is not None and tdx_root.is_dir() else None
    root = resolve_tdx_root(raw)
    if root is None:
        return []
    code = SymbolNormalizer.normalize_code(symbol)
    if len(code) != 6:
        return []
    paths = TdxLocalPaths(root)
    market_sh = SymbolNormalizer.market_id(code) == 1
    p = paths.lday_file(market_sh=market_sh, code6=code)
    rows = read_lday_file(p, tail=None)
    out: list[dict[str, Any]] = []
    for r in rows:
        out.append(
            {
                "date": r["date"],
                "open": float(r["open"]),
                "high": float(r["high"]),
                "low": float(r["low"]),
                "close": float(r["close"]),
                "volume": float(r["volume"]),
                "amount": float(r.get("amount") or 0),
            },
        )
    return out


def _merge_prefix_local_with_qfq(
    local: list[dict[str, Any]],
    qfq: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    if not qfq:
        return list(local)
    if not local:
        return list(qfq)

    df_q = pd.DataFrame(qfq)
    df_l = pd.DataFrame(local)
    df_q["date"] = pd.to_datetime(df_q["date"], errors='coerce')
    df_l = df_l.dropna(subset=["date"])
    df_q = df_q.sort_values("date").drop_duplicates(subset=["date"], keep="last")
    df_l = df_l.sort_values("date").drop_duplicates(subset=["date"], keep="last")

    min_q = df_q["date"].min()
    overlap_dates = df_l[df_l["date"] >= min_q]["date"].unique()

    ratios = []
    for d in overlap_dates[:10]:
        l_row = df_l[df_l["date"] == d]
        q_row = df_q[df_q["date"] == d]
        if not l_row.empty and not q_row.empty:
            lc = float(l_row.iloc[0]["close"])
            qc = float(q_row.iloc[0]["close"])
            if lc > 1e-9 and qc > 1e-9:
                ratios.append(qc / lc)

    ratio = 1.0
    if ratios:
        ratio = float(pd.Series(ratios).median())

    prefix = df_l[df_l["date"] < min_q].copy()
    if not prefix.empty and ratio != 1.0:
        for col in ("open", "high", "low", "close"):
            if col in prefix.columns:
                prefix[col] = prefix[col].astype(float) * ratio
        if "volume" in prefix.columns:
            prefix["volume"] = (prefix["volume"].astype(float) / ratio).round(0).astype(int)
        if "amount" in prefix.columns:
            prefix["amount"] = prefix["amount"].astype(float) / ratio

    merged = pd.concat([prefix, df_q], ignore_index=True)
    merged = merged.sort_values("date").drop_duplicates(subset=["date"], keep="last")
    merged["date"] = merged["date"].dt.strftime("%Y-%m-%d")
    return merged.to_dict("records")


def build_cn_ohlcv_merged(
    symbol: str,
    *,
    period: str = "2y",
    tdx_root: Path | str | None = None,
) -> tuple[list[dict[str, Any]], str]:
    """东财前复权为主；本地 lday 仅补充最早一段（按重叠日价做比例缩放近似对齐）。"""
    start_d, end_d = period_to_date_bounds(period)
    qfq, ev_q = fetch_cn_daily_qfq(symbol, start_d, end_d)
    rpath: Path | None = None
    if isinstance(tdx_root, Path) and tdx_root.is_dir():
        rpath = tdx_root
    elif isinstance(tdx_root, str) and tdx_root.strip():
        p = Path(tdx_root.strip())
        rpath = p if p.is_dir() else None
    local = load_cn_lday_bars(symbol, rpath)
    if qfq:
        merged = _merge_prefix_local_with_qfq(local, qfq)
        clip_s, clip_e = start_d, end_d
        merged = [b for b in merged if clip_s <= str(b.get("date", ""))[:10] <= clip_e]
        ev = f"{ev_q} 合并本地lday={len(local)}行 → 输出{len(merged)}行（前复权主路径）。"
        return merged, ev
    if local:
        loc_df = pd.DataFrame(local)
        # 使用 errors='coerce' 将无效日期转为 NaT，然后删除无效日期的行
        loc_df["date"] = pd.to_datetime(loc_df["date"], errors='coerce')
        loc_df = loc_df.dropna(subset=["date"])
        end_dt = pd.Timestamp(end_d)
        start_dt = pd.Timestamp(start_d)
        loc_df = loc_df[(loc_df["date"] >= start_dt) & (loc_df["date"] <= end_dt)]
        loc_df["date"] = loc_df["date"].dt.strftime("%Y-%m-%d")
        out = loc_df.to_dict("records")
        return out, f"AkShare 不可用，仅通达信本地未除权 lday {len(out)} 行。{ev_q}"
    return [], f"无K线: {ev_q} 且无本地lday。"
