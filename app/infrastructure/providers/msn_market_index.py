from __future__ import annotations
"""MSN global market index and hot stock provider."""


import requests
from datetime import datetime
from typing import Any

from ...core.logger import get_logger

logger = get_logger(__name__)


class MsnMarketIndexProvider:
    """Fetches real-time global market indices and hot stocks from MSN Finance API."""

    API_URL = "https://assets.msn.cn/service/Finance/Quotes"

    DEFAULT_INDICES = {
        "CN_SH": ["adfh77"],  # Shanghai Composite
        "CN_SZ": ["adg1m7"],  # Shenzhen Component
        "HK": ["ah7etc"],  # Hang Seng
        "JP": ["a9j7bh"],  # Nikkei 225
        "US_SP500": ["a33k6h"],  # S&P 500
        "US_NASDAQ": ["a3oxnm"],  # NASDAQ
        "US_DOW": ["a6qja2"],  # Dow Jones
        "UK": ["aopnp2"],  # FTSE 100
        "DE": ["afx2kr"],  # DAX
        "FR": ["aecfh7"],  # CAC 40
        "IN": ["ahkucw"],  # Sensex
    }

    HOT_STOCK_IDS = {
        "CN": [
            "ad88mw", "ad87qh", "auvwoc", "ad9b1h", "adci1h", "ad99yc",
            "adfha2", "adfif2", "adfnec", "ad95bh", "buegoc", "ad7m9c",
            "ad8n3m", "ad7ahw", "ad9fww", "ad7op2", "ad7k52",
        ],
        "HK": [
            "c3l227", "c1qnc7", "cjxlvh", "c2mr5r", "bwm8vh", "bwlwur",
            "cc7gzr", "c2y4xm", "c8c4xm", "c6xv52", "bwm33m",
        ],
        "US": [
            "bwm7tc", "bwm8pr", "bwm76h", "ad9ncw", "awrmfr", "c6vz9c",
            "ad8izr", "c8c827", "bwm73m", "aytir7",
        ],
    }

    def __init__(self, apikey: str | None = None):
        self._apikey = apikey or "0QfOX3Vn51YCzitbLaRkTTBadtWpgTN8NZLW0C1SEM"
        self._session = requests.Session()
        self._session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "application/json",
        })

    def _build_url(self, ids: list[str]) -> str:
        ids_str = ",".join(ids)
        activity_id = datetime.now().strftime("%Y%m%d%H%M%S")
        return f"{self.API_URL}?apikey={self._apikey}&activityId={activity_id}&ocid=finance-utils-peregrine&cm=zh-cn&it=web&scn=ANON&ids={ids_str}&wrapodata=false"

    def get_quotes(self, ids: list[str] | None = None) -> list[dict[str, Any]]:
        """Fetch quotes for given instrument IDs."""
        target_ids = ids or [i for inds in self.DEFAULT_INDICES.values() for i in inds]
        url = self._build_url(target_ids)
        try:
            resp = self._session.get(url, timeout=15)
            resp.raise_for_status()
            data = resp.json()
            if data and isinstance(data[0], list):
                return data[0]
            return data or []
        except Exception as e:
            logger.error(f"MSN market index fetch failed: {e}")
            return []

    def get_quotes_batch(self, ids: list[str]) -> list[dict[str, Any]]:
        """Fetch quotes one by one to avoid API issues."""
        results = []
        for id_ in ids:
            try:
                url = self._build_url([id_])
                resp = self._session.get(url, timeout=10)
                resp.raise_for_status()
                data = resp.json()
                if data and isinstance(data[0], list):
                    results.extend(data[0])
                elif data:
                    results.append(data[0] if isinstance(data[0], dict) else data)
            except Exception as e:
                logger.warning(f"MSN fetch failed for {id_}: {e}")
        return results

    def get_indices_by_market(self, market: str) -> list[dict[str, Any]]:
        """Fetch quotes for a specific market."""
        ids = self.DEFAULT_INDICES.get(market.upper(), [])
        if not ids:
            return []
        return self.get_quotes_batch(ids)

    def get_all_indices(self) -> list[dict[str, Any]]:
        """Fetch all default indices."""
        all_ids = [i for inds in self.DEFAULT_INDICES.values() for i in inds]
        return self.get_quotes_batch(all_ids)

    def to_market_quote(self, data: dict[str, Any]) -> dict[str, Any]:
        """Transform MSN quote to standardized format."""
        return {
            "symbol": data.get("symbol", data.get("instrumentId", "")),
            "name": data.get("displayName", data.get("shortName", "")),
            "price": data.get("price", 0),
            "change": data.get("priceChange", 0),
            "change_pct": data.get("priceChangePercent", 0),
            "high": data.get("priceDayHigh", 0),
            "low": data.get("priceDayLow", 0),
            "open": data.get("priceDayOpen", 0),
            "prev_close": data.get("pricePreviousClose", 0),
            "volume": data.get("accumulatedVolume", 0),
            "market": data.get("market", data.get("country", "")),
            "updated": data.get("timeLastUpdated", data.get("timeLastTraded", "")),
        }

    def get_hot_stocks(self, market: str = "CN") -> list[dict[str, Any]]:
        """Fetch hot/trending stocks for a market."""
        ids = self.HOT_STOCK_IDS.get(market.upper(), [])
        if not ids:
            ids = self.HOT_STOCK_IDS.get("CN", [])
        return self.get_quotes_batch(ids)

    def get_all_hot_stocks(self) -> list[dict[str, Any]]:
        """Fetch all hot stocks across markets."""
        all_ids = [i for ids in self.HOT_STOCK_IDS.values() for i in ids]
        return self.get_quotes_batch(all_ids)


_default_msn_index_provider: MsnMarketIndexProvider | None = None


def get_msn_index_provider() -> MsnMarketIndexProvider:
    global _default_msn_index_provider
    if _default_msn_index_provider is None:
        _default_msn_index_provider = MsnMarketIndexProvider()
    return _default_msn_index_provider
