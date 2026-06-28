from __future__ import annotations

"""Infrastructure mappers - convert between DB models and Domain entities."""


from datetime import datetime
from typing import Any

from app.domain.dto import BarData


class StockHistoryMapper:
    """Maps stock history DB model to domain BarData."""

    @staticmethod
    def to_bar_data(row: Any) -> BarData | None:
        """Convert DB row to BarData."""
        try:
            return BarData(
                code=str(getattr(row, 'stock_code', '') or ''),
                name=str(getattr(row, 'stock_name', '') or ''),
                trade_date=str(getattr(row, 'date', '') or ''),
                open=float(getattr(row, 'open', 0) or 0),
                high=float(getattr(row, 'high', 0) or 0),
                low=float(getattr(row, 'low', 0) or 0),
                close=float(getattr(row, 'close', 0) or 0),
                volume=float(getattr(row, 'volume', 0) or 0),
                amount=float(getattr(row, 'amount', 0) or 0),
            )
        except (TypeError, ValueError):
            return None

    @staticmethod
    def to_bar_data_from_dict(data: dict[str, Any]) -> BarData | None:
        """Convert dict to BarData."""
        try:
            return BarData(
                code=str(data.get("code", data.get("stock_code", "")) or ""),
                name=str(data.get("name", "") or ""),
                trade_date=str(data.get("trade_date", data.get("date", "") or "")),
                open=float(data.get("open", 0) or 0),
                high=float(data.get("high", 0) or 0),
                low=float(data.get("low", 0) or 0),
                close=float(data.get("close", data.get("price", 0) or 0)),
                volume=float(data.get("volume", 0) or 0),
                amount=float(data.get("amount", 0) or 0),
                turnover=float(data.get("turnover", 0) or 0),
                change_pct=float(data.get("change_pct", 0) or 0),
            )
        except (TypeError, ValueError):
            return None

    @staticmethod
    def to_bar_data_list(rows: list[Any]) -> list[BarData]:
        """Convert list of DB rows to BarData list."""
        return [r for r in (StockHistoryMapper.to_bar_data(row) for row in rows) if r is not None]


class QuoteMapper:
    """Maps quote data from various sources to QuoteData."""

    @staticmethod
    def from_akshare(data: dict[str, Any]) -> dict[str, Any]:
        """Convert AkShare quote format to standard format."""
        return {
            "code": str(data.get("code", "") or data.get("symbol", "") or ""),
            "name": str(data.get("name", "") or data.get("名称", "") or ""),
            "price": float(data.get("price", data.get("最新价", 0) or 0)),
            "change_amount": float(data.get("change_amount", data.get("涨跌额", 0) or 0)),
            "change_pct": float(data.get("change_pct", data.get("涨跌幅", 0) or 0)),
            "open": float(data.get("open", data.get("今开", 0) or 0)),
            "high": float(data.get("high", data.get("最高", 0) or 0)),
            "low": float(data.get("low", data.get("最低", 0) or 0)),
            "volume": float(data.get("volume", data.get("成交量", 0) or 0)),
            "amount": float(data.get("amount", data.get("成交额", 0) or 0)),
            "pe": data.get("pe") or None,
            "pb": data.get("pb") or None,
            "timestamp": datetime.now(),
        }


class LonghuMapper:
    """Maps longhu (dragon-tiger list) data."""

    @staticmethod
    def to_domain(data: dict[str, Any]) -> dict[str, Any]:
        """Convert longhu data to standardized format."""
        return {
            "code": str(data.get("code", data.get("股票代码", "") or "")),
            "name": str(data.get("name", data.get("股票名称", "") or "")),
            "reason": str(data.get("reason", data.get("上榜理由", "") or "")),
            "trade_date": str(data.get("trade_date", data.get("交易日期", "") or "")),
            "buy_amount": float(data.get("buy_amount", data.get("龙虎榜买入", 0) or 0)),
            "sell_amount": float(data.get("sell_amount", data.get("龙虎榜卖出", 0) or 0)),
            "net_amount": float(data.get("net_amount", data.get("净额", 0) or 0)),
        }
