from __future__ import annotations

"""Build a stock detail timeline that aligns market data with evidence events."""

from datetime import date, datetime, timedelta
from typing import Any

from app.domain.enums import MarketCode


class AttributionTimelineService:
    """Collect lightweight evidence markers for chart overlays."""

    def __init__(
        self,
        *,
        stock_service: Any = None,
        news_archive: Any = None,
        fundamental_access: Any = None,
        basic_market_data_service: Any = None,
    ) -> None:
        self._stock_service = stock_service
        self._news_archive = news_archive
        self._fundamental_access = fundamental_access
        self._basic_market_data_service = basic_market_data_service

    def build_timeline(
        self,
        symbol: str,
        market: MarketCode = MarketCode.CN,
        *,
        start: str | None = None,
        end: str | None = None,
        limit: int = 80,
    ) -> dict[str, Any]:
        symbol = (symbol or "").strip()
        end_date = self._parse_date(end) or date.today()
        start_date = self._parse_date(start) or (end_date - timedelta(days=60))
        markers: list[dict[str, Any]] = []
        gaps: list[str] = []

        for loader in (
            self._load_news_markers,
            self._load_report_markers,
            self._load_longhu_markers,
            self._load_price_action_markers,
        ):
            try:
                markers.extend(loader(symbol, market, start_date, end_date, limit))
            except Exception as exc:
                gaps.append(f"{loader.__name__.replace('_load_', '').replace('_markers', '')}: {exc}")

        filtered = [
            marker
            for marker in markers
            if start_date <= self._parse_date(marker.get("date")) <= end_date
        ]
        filtered.sort(key=lambda item: (item.get("date") or "", item.get("type") or ""))
        limited = filtered[-limit:]
        return {
            "symbol": symbol,
            "market": market.value,
            "start": start_date.isoformat(),
            "end": end_date.isoformat(),
            "markers": limited,
            "summary": self._summary(limited),
            "data_gaps": gaps,
        }

    def _load_news_markers(
        self,
        symbol: str,
        market: MarketCode,
        start: date,
        end: date,
        limit: int,
    ) -> list[dict[str, Any]]:
        if self._news_archive is None:
            return []
        items = self._news_archive.list_for_symbol(market.value, symbol, limit=limit) or []
        markers = []
        for item in items:
            row = self._to_dict(item)
            dt = self._first(row, "published_at", "publish_time", "datetime", "date", "created_at")
            title = self._first(row, "title", "headline", "summary", default="news")
            markers.append(
                self._marker(
                    dt,
                    "news",
                    "news",
                    title,
                    row,
                    sentiment=row.get("signal_tag") or row.get("sentiment"),
                )
            )
        return markers

    def _load_report_markers(
        self,
        symbol: str,
        market: MarketCode,
        start: date,
        end: date,
        limit: int,
    ) -> list[dict[str, Any]]:
        if market != MarketCode.CN or self._fundamental_access is None:
            return []
        rows, err = self._fundamental_access.cn_research_reports(symbol, limit=min(limit, 50))
        if err:
            return []
        markers = []
        for row in rows or []:
            data = self._to_dict(row)
            dt = self._first(data, "date", "publish_date", "report_date", "datetime", "time")
            title = self._first(data, "title", "name", "report_title", default="research report")
            markers.append(self._marker(dt, "research_report", "report", title, data))
        return markers

    def _load_longhu_markers(
        self,
        symbol: str,
        market: MarketCode,
        start: date,
        end: date,
        limit: int,
    ) -> list[dict[str, Any]]:
        if market != MarketCode.CN or self._basic_market_data_service is None:
            return []
        items = self._basic_market_data_service.longhu_for_stock(symbol, limit=min(limit, 50)) or []
        markers = []
        for item in items:
            row = self._to_dict(item)
            dt = self._first(row, "trade_date", "date")
            title = self._first(row, "reason", "name", "title", default="longhu activity")
            markers.append(self._marker(dt, "large_order", "activity", title, row))
        return markers

    def _load_price_action_markers(
        self,
        symbol: str,
        market: MarketCode,
        start: date,
        end: date,
        limit: int,
    ) -> list[dict[str, Any]]:
        if self._stock_service is None:
            return []
        history = self._stock_service.get_history(symbol, market, start.isoformat(), end.isoformat())
        rows = history if isinstance(history, list) else self._to_dict(history).get("history", [])
        markers = []
        previous_close = None
        for row in rows or []:
            data = self._to_dict(row)
            close = self._safe_float(data.get("close"))
            volume = self._safe_float(data.get("volume"))
            pct = self._safe_float(data.get("change_pct"))
            if pct is None and previous_close and close:
                pct = (close - previous_close) / previous_close * 100
            if close:
                previous_close = close
            if pct is not None and abs(pct) >= 7:
                markers.append(
                    self._marker(
                        self._first(data, "date", "trade_date", "datetime"),
                        "price_move",
                        "market",
                        "large price move",
                        {"change_pct": round(pct, 2), "close": close},
                    )
                )
            if volume is not None and volume > 0 and self._safe_float(data.get("amount")):
                amount = self._safe_float(data.get("amount")) or 0
                if amount >= 100000000:
                    markers.append(
                        self._marker(
                            self._first(data, "date", "trade_date", "datetime"),
                            "volume_spike",
                            "market",
                            "high turnover",
                            {"amount": amount, "volume": volume},
                        )
                    )
        return markers

    @staticmethod
    def _marker(
        raw_date: Any,
        marker_type: str,
        lane: str,
        title: Any,
        payload: dict[str, Any],
        **extra: Any,
    ) -> dict[str, Any]:
        dt = AttributionTimelineService._parse_date(raw_date)
        marker = {
            "date": dt.isoformat() if dt else "",
            "type": marker_type,
            "lane": lane,
            "title": str(title or marker_type)[:120],
            "payload": payload,
        }
        marker.update({k: v for k, v in extra.items() if v is not None})
        return marker

    @staticmethod
    def _summary(markers: list[dict[str, Any]]) -> dict[str, Any]:
        by_type: dict[str, int] = {}
        for marker in markers:
            by_type[marker["type"]] = by_type.get(marker["type"], 0) + 1
        return {
            "count": len(markers),
            "by_type": by_type,
            "has_evidence": bool(markers),
        }

    @staticmethod
    def _to_dict(item: Any) -> dict[str, Any]:
        if isinstance(item, dict):
            return dict(item)
        if hasattr(item, "model_dump"):
            return item.model_dump()
        if hasattr(item, "dict"):
            return item.dict()
        return dict(getattr(item, "__dict__", {}) or {})

    @staticmethod
    def _first(row: dict[str, Any], *keys: str, default: Any = "") -> Any:
        for key in keys:
            value = row.get(key)
            if value not in (None, ""):
                return value
        return default

    @staticmethod
    def _safe_float(value: Any) -> float | None:
        try:
            if value in (None, ""):
                return None
            return float(value)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _parse_date(value: Any) -> date:
        if isinstance(value, datetime):
            return value.date()
        if isinstance(value, date):
            return value
        text = str(value or "").strip()
        if not text:
            return date.min
        text = text[:10].replace("/", "-")
        if len(text) == 8 and text.isdigit():
            text = f"{text[:4]}-{text[4:6]}-{text[6:]}"
        try:
            return datetime.fromisoformat(text).date()
        except ValueError:
            return date.min


__all__ = ["AttributionTimelineService"]
