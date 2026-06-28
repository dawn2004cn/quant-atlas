from __future__ import annotations

"""QuestDB / ClickHouse history adapters for MultiSourceHistoryProvider."""

from datetime import date

from app.domain.enums import MarketCode
from app.infrastructure.timeseries.ohlcv_history_reader import (
    fetch_clickhouse_ohlcv,
    fetch_questdb_ohlcv,
)


class QuestDBHistoryAdapter:
    """QuestDB ``stock_history`` (or ``QUESTDB_OHLCV_TABLE``)."""

    def get_history(self, symbol: str, market: MarketCode, start_date: date, end_date: date) -> list[dict]:
        return fetch_questdb_ohlcv(symbol, market, start_date, end_date)


class ClickHouseHistoryAdapter:
    """ClickHouse OHLCV table when ``CLICKHOUSE_OHLCV_TABLE`` is set."""

    def get_history(self, symbol: str, market: MarketCode, start_date: date, end_date: date) -> list[dict]:
        return fetch_clickhouse_ohlcv(symbol, market, start_date, end_date)
