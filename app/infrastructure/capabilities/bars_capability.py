from __future__ import annotations
"""Bars / OHLCV data capability."""


from datetime import date, timedelta
from typing import Any

from app.domain.capabilities.base import BaseCapability
from app.domain.enums import MarketCode
from app.infrastructure.capabilities.registry import capability


def _period_to_days(period: str) -> int:
    p = (period or "1y").strip().lower()
    mapping = {
        "5d": 5, "1m": 30, "3m": 91, "6m": 182,
        "1y": 365, "2y": 730, "5y": 1825, "max": 3650,
    }
    return mapping.get(p, 365)


@capability("fetch_bars")
class BarsCapability(BaseCapability):
    """Fetch OHLCV bar history for a symbol."""

    capability_name = "fetch_bars"

    def __init__(self, **services: Any) -> None:
        self._market_provider = services.get("market_provider")

    def execute(
        self,
        symbol: str,
        market: MarketCode,
        *,
        period: str = "1y",
        interval: str = "1d",
    ) -> tuple[list[dict], str]:
        days = _period_to_days(period)
        end = date.today()
        start = end - timedelta(days=days)
        note = (
            f"行情来源: MarketDataProvider.get_stock_history; "
            f"区间 {start.isoformat()}~{end.isoformat()} (period={period})."
        )
        if interval != "1d":
            note += f" 当前引擎以日线为主，interval={interval} 映射为日线序列。"
        try:
            bars = self._market_provider.get_stock_history(
                symbol, market, start.isoformat(), end.isoformat()
            )
        except Exception as exc:
            return [], f"{note} 拉取失败: {exc!s}."
        return list(bars or []), f"{note} 共 {len(bars or [])} 条。"
