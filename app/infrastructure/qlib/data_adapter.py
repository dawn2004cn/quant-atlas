from __future__ import annotations
"""从平台行情 +（A 股）东财前复权与本地通达信 lday 合并，对齐 Qlib 日频最小契约。"""


from typing import Any

import pandas as pd

from ...domain.enums import MarketCode
from ...domain.ports import ToolFacadePort


import logging
logger = logging.getLogger(__name__)
class QlibDataAdapter:
    """Normalized bar provider for Qlib pipelines, backed by a ToolFacadePort."""

    def __init__(
        self,
        data_access: ToolFacadePort,
        *,
        tdx_root_path: str | None = None,
        stock_cache: Any | None = None,
    ) -> None:
        self._da = data_access
        self._tdx_root = (tdx_root_path or "").strip() or None
        self._stock_cache = stock_cache

    def fetch_daily_bars(
        self,
        symbol: str,
        market: MarketCode,
        *,
        period: str = "2y",
    ) -> tuple[list[dict[str, Any]], str]:
        """返回规范化行: date, open, high, low, close, volume（字符串日期 YYYY-MM-DD）。"""
        if market == MarketCode.CN:
            from .cn_ohlcv_merge import build_cn_ohlcv_merged

            merged, ev_merge = build_cn_ohlcv_merged(
                symbol,
                period=period,
                tdx_root=self._tdx_root,
            )
            bars = self._normalize_bar_list(merged)
            if bars:
                self._persist_cn_cache(symbol, bars)
                return bars, ev_merge

        bars, evidence = self._da.fetch_bars(symbol, market, period=period, interval="1d")
        out = self._normalize_bar_list(bars)
        return out, evidence

    @staticmethod
    def _normalize_bar_list(bars: list[dict[str, Any]]) -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []
        for b in bars or []:
            ds = str(b.get("date") or b.get("Date") or "")[:10]
            if not ds:
                continue
            try:
                o = float(b.get("open") or 0)
                h = float(b.get("high") or 0)
                l_ = float(b.get("low") or 0)
                c = float(b.get("close") or 0)
                v = float(b.get("volume") or 0)
                a = float(b.get("amount") or b.get("Amount") or 0)
            except (TypeError, ValueError):
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

    def _persist_cn_cache(self, symbol: str, bars: list[dict[str, Any]]) -> None:
        if self._stock_cache is None or not bars:
            return
        try:
            from ..mappers.symbol_normalizer import SymbolNormalizer

            key = SymbolNormalizer.to_db_code(symbol, market="CN")
            rows: list[dict[str, Any]] = []
            for b in bars:
                rows.append(
                    {
                        "date": b["date"],
                        "open": b["open"],
                        "high": b["high"],
                        "low": b["low"],
                        "close": b["close"],
                        "volume": b["volume"],
                        "amount": b.get("amount", 0.0),
                    },
                )
            self._stock_cache.save_stock_history(key, rows)
        except Exception:  # noqa: BLE001 as e:
            logger.warning("data_adapter.py._persist_cn_cache: %s", e)

    def bars_to_dataframe(self, bars: list[dict[str, Any]]) -> pd.DataFrame:
        if not bars:
            return pd.DataFrame(columns=["date", "open", "high", "low", "close", "volume"])
        df = pd.DataFrame(bars)
        # 使用 errors='coerce' 将无效日期转为 NaT，然后删除无效日期的行
        df["date"] = pd.to_datetime(df["date"], errors='coerce')
        df = df.dropna(subset=["date"])
        return df.sort_values("date").reset_index(drop=True)
