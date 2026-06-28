"""Bridge: register MultiSourceHistoryProvider as a DataLakeManager data source.

Allows DataLakeManager to query all 8 history adapters directly instead of
going through market_service.get_history(), eliminating the dual-path confusion.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from app.core.logger import get_logger

if TYPE_CHECKING:
    import pandas as pd

    from app.core.mesh.unified_data_lake import DataQuery

logger = get_logger(__name__)


class MultiSourceBridge:
    """Adapts MultiSourceHistoryProvider to DataLakeManager's fallback interface."""

    def __init__(self) -> None:
        self._provider = None

    def _lazy_provider(self):
        if self._provider is None:
            from app.infrastructure.providers.history_adapters import (
                MultiSourceHistoryProvider,
            )
            self._provider = MultiSourceHistoryProvider()
        return self._provider

    async def fetch_fallback(self, query: DataQuery) -> tuple[pd.DataFrame, list[str]]:
        """Fetch from the multi-source chain; returns (DataFrame, warnings)."""
        from datetime import date

        import pandas as pd

        market_raw = (query.market or "CN").upper()
        from app.domain.enums import MarketCode
        market = MarketCode.CN
        if market_raw in ("HK",):
            market = MarketCode.HK
        elif market_raw == "US":
            market = MarketCode.US

        start = query.start_date if query.start_date else date(2000, 1, 1)
        end = query.end_date if query.end_date else date.today()
        if hasattr(start, "strftime"):
            start = start.date() if hasattr(start, "date") else date.fromisoformat(str(start)[:10])
        if hasattr(end, "strftime"):
            end = end.date() if hasattr(end, "date") else date.fromisoformat(str(end)[:10])

        provider = self._lazy_provider()
        bars = provider.get_history(query.symbol, market, start, end)
        if not bars:
            return pd.DataFrame(), ["MultiSourceHistoryProvider returned empty"]

        df = pd.DataFrame(bars)
        if df.empty:
            return df, ["Empty DataFrame from multi-source fallback"]

        time_col = next(
            (c for c in df.columns if c.lower() in ("date", "timestamp", "time", "trade_date")),
            None,
        )
        if time_col:
            df[time_col] = pd.to_datetime(df[time_col], errors="coerce")
            df = df.set_index(time_col)

        close_col = next((c for c in df.columns if "close" in c.lower()), None)
        if close_col and close_col != "close":
            df = df.rename(columns={close_col: "close"})

        logger.info("MultiSourceBridge delivered %d bars for %s", len(df), query.symbol)
        return df, [f"data_source:multi_source({provider.last_source})"]
