from __future__ import annotations
"""读取通达信 ``vipdoc/*/lday/*.day`` 未除权日线（与 ``stock-analysis.func.day2csv`` 同一 32 字节结构）。"""


from decimal import Decimal
from pathlib import Path
from struct import unpack
from typing import Any

import pandas as pd


def parse_lday_bytes(buf: bytes) -> list[dict[str, Any]]:
    """32 字节/条：日期 uint32、OHLC uint32×4、成交额 float、成交量 uint32、保留 uint32。"""
    n = len(buf) // 32
    rows: list[dict[str, Any]] = []
    for i in range(n):
        begin = i * 32
        chunk = buf[begin : begin + 32]
        if len(chunk) < 32:
            break
        a = unpack("IIIIIfII", chunk)
        ds = str(a[0])
        if len(ds) < 8:
            continue
        date_s = f"{ds[0:4]}-{ds[4:6]}-{ds[6:8]}"
        amt = int(Decimal(a[5]).quantize(Decimal("1."), rounding="ROUND_HALF_UP"))
        rows.append(
            {
                "date": date_s,
                "open": round(a[1] / 100.0, 4),
                "high": round(a[2] / 100.0, 4),
                "low": round(a[3] / 100.0, 4),
                "close": round(a[4] / 100.0, 4),
                "volume": int(a[6]),
                "amount": amt,
            },
        )
    return rows


def read_lday_file(path: Path, *, tail: int | None = None) -> list[dict[str, Any]]:
    p = Path(path)
    if not p.is_file():
        return []
    data = p.read_bytes()
    rows = parse_lday_bytes(data)
    if tail is not None and tail > 0 and len(rows) > tail:
        return rows[-tail:]
    return rows


def _get_tdx_market_code(market: str) -> int:
    """CN 市场代码转 TDX 市场代码"""
    return {"sh": 1, "sz": 0, "bj": 0}.get(market, 0)


def _fetch_xdxr_from_tdx(market: str, code: str) -> pd.DataFrame:
    from ...infrastructure.external.tdx_manager import TdxConnectionManager

    tdx_mgr = TdxConnectionManager()
    market_code = _get_tdx_market_code(market)
    xdxr_data = tdx_mgr.execute("get_xdxr_info", market_code, code)
    if not xdxr_data:
        return pd.DataFrame()
    df_xdxr = pd.DataFrame(xdxr_data)
    df_xdxr = df_xdxr[df_xdxr["category"] == 1].copy()
    if df_xdxr.empty:
        return pd.DataFrame()
    df_xdxr["date"] = pd.to_datetime(
        df_xdxr["year"].astype(str)
        + "-"
        + df_xdxr["month"].astype(str).str.zfill(2)
        + "-"
        + df_xdxr["day"].astype(str).str.zfill(2)
    )
    df_xdxr.set_index("date", inplace=True)
    return df_xdxr[["fenhong", "songzhuangu", "peigu", "peigujia"]].astype(float)


def fetch_xdxr_data(market: str, code: str) -> pd.DataFrame:
    """获取除权除息数据（进程内 LRU 缓存 + 并发限流）。"""
    from .xdxr_cache import get_cached_xdxr

    try:
        return get_cached_xdxr(market, code, _fetch_xdxr_from_tdx)
    except Exception:
        return pd.DataFrame()


def apply_qfq(rows: list[dict[str, Any]], market: str, code: str) -> list[dict[str, Any]]:
    """对 rows 应用前复权转换"""
    if not rows:
        return rows
    df_xdxr = fetch_xdxr_data(market, code)
    if df_xdxr.empty:
        return rows
    from .qfq_calculator import compute_qfq_factors_from_xdxr, apply_qfq_to_rows
    factors = compute_qfq_factors_from_xdxr(rows, df_xdxr)
    return apply_qfq_to_rows(rows, factors)


def read_lday_file_with_qfq(path: Path, market: str, code: str, *, tail: int | None = None) -> list[dict[str, Any]]:
    """读取 TDX 日 K 文件并应用前复权"""
    rows = read_lday_file(path, tail=tail)
    return apply_qfq(rows, market, code)

if __name__ == "__main__":
    TDX_ROOT_PATH = r"E:\tdx\通达信金融终端(开心果交易版)V2024.02"
    from .paths import TdxLocalPaths
    paths = TdxLocalPaths(Path(TDX_ROOT_PATH))
    day_file = paths.lday_file_by_market(market="sh", code6="600519")
    rows = read_lday_file_with_qfq(day_file, market="sh", code="600519")
    for row in rows[-5:]:
        print(row)