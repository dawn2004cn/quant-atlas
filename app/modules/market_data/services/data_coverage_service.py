from __future__ import annotations

"""Symbol-level K-line coverage for analysis trust warnings."""

from datetime import date, timedelta
from typing import Any

from app.domain.dto.data_coverage_dto import DataCoverageDTO
from app.domain.enums import MarketCode
from app.domain.shared.data_coverage import assess_bar_coverage


class DataCoverageService:
    """Fetch recent history and assess session coverage."""

    def __init__(self, stock_service: Any | None = None) -> None:
        self._stock_service = stock_service

    @staticmethod
    def _trading_day_fn(market: MarketCode):
        if market == MarketCode.CN:
            from app.infrastructure.calendar.cn_sse_calendar import is_cn_equity_trading_day

            return is_cn_equity_trading_day
        from app.domain.shared.data_coverage import _weekday_trading_day

        return _weekday_trading_day

    @staticmethod
    def _extract_dates(history: list[Any]) -> list[str]:
        dates: list[str] = []
        for row in history or []:
            if isinstance(row, dict):
                d = row.get("date") or row.get("Date") or row.get("trade_date")
            else:
                d = getattr(row, "date", None)
            if d:
                dates.append(str(d)[:10])
        return dates

    def assess_symbol(
        self,
        symbol: str,
        market: MarketCode | str = MarketCode.CN,
        *,
        lookback_days: int = 30,
    ) -> DataCoverageDTO:
        mkt = market if isinstance(market, MarketCode) else MarketCode(str(market or "CN").upper())
        sym = str(symbol or "").strip().upper()
        end = date.today()
        start = end - timedelta(days=lookback_days + 14)
        bar_dates: list[str] = []
        if self._stock_service and sym:
            try:
                raw = self._stock_service.get_history(sym, mkt, start.isoformat(), end.isoformat())
                bar_dates = self._extract_dates(raw if isinstance(raw, list) else [])
            except Exception:
                bar_dates = []
        metrics = assess_bar_coverage(
            bar_dates,
            lookback_days=lookback_days,
            as_of=end,
            is_trading_day=self._trading_day_fn(mkt),
        )
        return DataCoverageDTO(symbol=sym, market=mkt.value, **metrics)


__all__ = ["DataCoverageService"]
