from __future__ import annotations
"""OpenBB implementation of MarketDataProvider."""


import logging
import os
from datetime import datetime
from typing import Any

from openbb import obb

from app.domain.ports import MarketDataProvider
from app.domain.entities import StockQuote, ChipDistribution
from app.domain.enums import MarketCode

from app.core.circuit_breaker import CircuitBreakerOpenError, circuit_breaker
from app.core.logger import get_logger
from app.core.middleware.degraded_context import mark_system_degraded

logger = get_logger(__name__)


def _set_fmp_credentials() -> None:
    """Set FMP API key for OpenBB from env."""
    api_key = os.getenv("FMP_API_KEY", "").strip()
    if api_key:
        try:
            obb.user.credentials.add("fmp", api_key)
        except Exception as e:
            logger.warning("openbb_adapter.py._set_fmp_credentials: %s", e)

class OpenBBDataProvider(MarketDataProvider):
    def __init__(self, default_provider: str = "yfinance"):
        self._default_provider = default_provider

    def get_market_overview(self, market: MarketCode) -> dict[str, Any]:
        return {"market": market.value, "source": "openbb"}

    def get_market_rankings(self, market: MarketCode) -> dict[str, list[dict[str, Any]]]:
        return {"rankings": []}

    def get_realtime_quotes(
        self,
        symbols: list[str] | None = None,
        market: MarketCode = MarketCode.CN,
    ) -> list[StockQuote]:
        if not symbols:
            return []
        
        providers = self._get_provider_chain(market)
        
        for provider in providers:
            try:
                quotes = self._fetch_quotes_internal(symbols, market, provider)
            except CircuitBreakerOpenError:
                logger.warning("OpenBB quotes circuit open; skipping provider %s", provider)
                mark_system_degraded("openbb")
                continue
            if quotes:
                return quotes
        
        return []
    
    @circuit_breaker("openbb_quotes", failure_threshold=3, timeout=60)
    def _fetch_quotes_internal(
        self,
        symbols: list[str],
        market: MarketCode,
        provider: str
    ) -> list[StockQuote]:
        """Internal fetch with specific provider."""
        normalized = [self._normalize_symbol(s, market) for s in symbols]
        sym_str = ",".join(normalized)
        
        quotes = []
        try:
            res = obb.equity.price.quote(symbol=sym_str, provider=provider)
            data = res.to_dict()
            if isinstance(data, list):
                for item in data:
                    quotes.append(self._map_to_quote(item))
            else:
                quotes.append(self._map_to_quote(data))
        except Exception as e:
            logger.warning(f"OpenBB quote failed ({provider}) for {sym_str}: {e}")
            if len(symbols) > 1:
                for s in symbols:
                    try:
                        res = obb.equity.price.quote(symbol=self._normalize_symbol(s, market), provider=provider)
                        data = res.to_dict()
                        quotes.append(self._map_to_quote(data))
                    except Exception as e:
                        logger.warning("openbb_adapter.py._fetch_quotes_internal: %s", e)
        
        return quotes
    
    def get_stock_profile(self, symbol: str, market: MarketCode) -> dict[str, Any]:
        try:
            return self._fetch_profile_internal(symbol, market)
        except CircuitBreakerOpenError:
            logger.warning("OpenBB profile circuit open for %s", symbol)
            mark_system_degraded("openbb")
            return {}

    @circuit_breaker("openbb_profile", failure_threshold=3, timeout=60)
    def _fetch_profile_internal(self, symbol: str, market: MarketCode) -> dict[str, Any]:
        provider = self._get_provider_for_market(market)
        sym = self._normalize_symbol(symbol, market)
        try:
            res = obb.equity.profile(symbol=sym, provider=provider)
            return res.to_dict()
        except Exception as e:
            logger.warning(f"OpenBB profile failed: {e}")
            return {}

    def get_stock_history(
        self,
        symbol: str,
        market: MarketCode,
        start: str,
        end: str,
    ) -> list[dict[str, Any]]:
        providers = self._get_provider_chain(market)
        
        for provider in providers:
            try:
                result = self._fetch_history_internal(symbol, market, start, end, provider)
            except CircuitBreakerOpenError:
                logger.warning("OpenBB history circuit open; skipping provider %s", provider)
                mark_system_degraded("openbb")
                continue
            if result:
                return result
        
        return []

    @circuit_breaker("openbb_history", failure_threshold=3, timeout=60)
    def _fetch_history_internal(
        self,
        symbol: str,
        market: MarketCode,
        start: str,
        end: str,
        provider: str
    ) -> list[dict[str, Any]]:
        """Internal fetch history with specific provider."""
        sym = self._normalize_symbol(symbol, market)
        try:
            res = obb.equity.price.historical(
                symbol=sym,
                start_date=start,
                end_date=end,
                provider=provider
            )
            raw = res.to_dict()
            return self._convert_to_row_format(raw)
        except Exception as e:
            logger.warning(f"OpenBB history failed ({provider}) for {sym}: {e}")
            return []

    def _normalize_symbol(self, symbol: str, market: MarketCode) -> str:
        """Normalize symbol for OpenBB provider."""
        s = symbol.strip()
        if market == MarketCode.HK and not s.endswith(".HK"):
            return f"{s}.HK"
        if market == MarketCode.US and not s.endswith(".O") and not s.isdigit() and len(s) <= 5:
            return s.upper()
        return s

    def _convert_to_row_format(self, raw: dict[str, Any]) -> list[dict[str, Any]]:
        """Convert OpenBB columnar format to row format for frontend."""
        if not raw:
            return []
        dates = raw.get("date") or raw.get("Date") or raw.get("Datetime") or raw.get("datetime")
        if not dates:
            return []
        if isinstance(dates, str):
            return self._convert_string_format(raw)
        if isinstance(dates, list):
            if len(dates) == 1 and isinstance(dates[0], str):
                return self._convert_string_format(raw)
            if len(dates) == 0:
                return []
            rows = []
            for i in range(len(dates)):
                row: dict[str, Any] = {}
                for k, v in raw.items():
                    if isinstance(v, list) and i < len(v):
                        row[k] = v[i]
                rows.append(row)
            return [self._serialize_bar(r) for r in rows]
        return []

    def _convert_string_format(self, raw: dict[str, Any]) -> list[dict[str, Any]]:
        """Convert string-separated format to row format."""
        rows = []
        date_str = str(raw.get("date") or raw.get("Date") or "")
        dates = date_str.split() if date_str else []
        for i, d in enumerate(dates):
            row: dict[str, Any] = {"date": d}
            for k, v in raw.items():
                if k == "date" or k == "Date":
                    continue
                val = str(v)
                parts = val.split() if val else []
                if i < len(parts):
                    try:
                        row[k] = float(parts[i])
                    except (ValueError, TypeError):
                        row[k] = parts[i]
            rows.append(row)
        return rows

    def _serialize_bar(self, bar: dict[str, Any]) -> dict[str, Any]:
        """Serialize date objects to ISO strings for JSON compatibility."""
        out: dict[str, Any] = {}
        for k, v in bar.items():
            if hasattr(v, "isoformat"):
                out[k] = v.isoformat()
            elif isinstance(v, list):
                out[k] = [item.isoformat() if hasattr(item, "isoformat") else item for item in v]
            elif isinstance(v, dict):
                out[k] = {kk: vv.isoformat() if hasattr(vv, "isoformat") else vv for kk, vv in v.items()}
            else:
                out[k] = v
        return out

    def get_chip_distribution(self, symbol: str, market: MarketCode) -> ChipDistribution | None:
        return None

    def _get_provider_chain(self, market: MarketCode) -> list[str]:
        """Get provider chain for fallback. FMP preferred if API key available, then yfinance."""
        fmp_key = os.getenv("FMP_API_KEY", "").strip()
        
        chain = []
        if fmp_key:
            chain.append("fmp")
        chain.append("yfinance")
        return chain if chain else ["yfinance"]

    def _get_provider_for_market(self, market: MarketCode) -> str:
        return "yfinance"

    def _map_to_quote(self, item: dict[str, Any]) -> StockQuote:
        return StockQuote(
            code=item.get("symbol", ""),
            name=item.get("name", ""),
            market=MarketCode.US if self._default_provider != "yfinance" else MarketCode.CRYPTO,
            price=item.get("last_price", item.get("price", 0.0)),
            change_pct=item.get("change_percent", 0.0),
            volume=item.get("volume", 0.0),
            source="openbb"
        )