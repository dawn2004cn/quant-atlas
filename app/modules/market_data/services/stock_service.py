from __future__ import annotations
from app.domain.dto.service_result import GenericResponseDTO
"""Stock Services - Stock data services with typed DTOs."""


from typing import Any, Optional

from app.core.logger import get_logger
from app.domain.dto import BarData, IndicatorResult, HistoryData
from app.domain.enums import MarketCode
from app.domain.shared.symbol_normalizer import SymbolNormalizer
from app.core.base_service import BaseApplicationService

logger = get_logger(__name__)


def _resolve_market_code(market: str | MarketCode) -> MarketCode:
    raw = market.value if isinstance(market, MarketCode) else str(market or "CN")
    upper = raw.upper()
    if upper in ("A", "CN"):
        return MarketCode.CN
    return MarketCode(upper)


def _code6(symbol: str) -> str:
    return "".join(ch for ch in str(symbol) if ch.isdigit())[-6:].zfill(6)


def _quote_to_realtime(code: str, quote: object) -> GenericResponseDTO:
    """Map provider quote entity to frontend realtime profile dict."""
    name = getattr(quote, "name", None) or ""
    price = float(getattr(quote, "price", 0) or 0)
    change_amount = float(getattr(quote, "change_amount", getattr(quote, "change", 0)) or 0)
    return {
        "code": getattr(quote, "code", None) or code,
        "name": name,
        "price": price,
        "change_amount": change_amount,
        "change_pct": float(getattr(quote, "change_pct", 0) or 0),
        "volume": float(getattr(quote, "volume", 0) or 0),
        "amount": float(getattr(quote, "amount", 0) or 0),
        "turnover": float(getattr(quote, "turnover", 0) or 0),
        "pe": getattr(quote, "pe", None),
        "pb": getattr(quote, "pb", None),
        "total_market_cap": float(getattr(quote, "total_market_cap", 0) or 0),
        "industry": getattr(quote, "industry", "") or "",
        "open_price": float(getattr(quote, "open_price", 0) or 0),
        "high_price": float(getattr(quote, "high_price", 0) or 0),
        "low_price": float(getattr(quote, "low_price", 0) or 0),
        "prev_close": float(getattr(quote, "prev_close", 0) or 0),
        "volume_ratio": float(getattr(quote, "volume_ratio", 0) or 0),
        "amplitude": float(getattr(quote, "amplitude", 0) or 0),
    }


class StockDetailResult:
    """Typed stock detail result."""
    def __init__(self, code: str, market: str, profile: dict, indicators: dict):
        self.code = code
        self.market = market
        self.profile = profile
        self.indicators = indicators

    def to_dict(self) -> GenericResponseDTO[str, object]:
        return {
            "code": self.code,
            "market": self.market,
            "profile": self.profile,
            "indicators": self.indicators,
        }


class StockApplicationService(BaseApplicationService):
    """Stock data service with typed DTO contracts."""

    def __init__(
        self,
        market_provider=None,
        indicator_provider=None,
        news_provider=None,
        global_market_service=None,
        stock_cache=None,
    ):
        super().__init__()
        self._market_provider = market_provider
        self._indicator_provider = indicator_provider
        self._news_provider = news_provider
        self._global_market_service = global_market_service
        self._stock_cache = stock_cache

    def get_stock_detail(self, code: str, market: str | MarketCode = "A") -> StockDetailResult:
        """Get stock detail with fundamental data and indicators."""
        market_code = _resolve_market_code(market)
        market_label = market_code.value
        lookup_code = SymbolNormalizer().normalize(code) if market_code == MarketCode.CN else code.strip()
        profile: dict[str, Any] = {"realtime": {}, "name": "", "industry": ""}

        if self._market_provider and hasattr(self._market_provider, "get_realtime_quotes"):
            try:
                quotes = self._market_provider.get_realtime_quotes([lookup_code], market_code)
                if quotes:
                    realtime = _quote_to_realtime(code, quotes[0])
                    profile["realtime"] = realtime
                    profile["name"] = realtime.get("name") or ""
                    profile["industry"] = realtime.get("industry") or ""
                else:
                    profile["realtime"] = self._get_stock_from_cache(code, market_code)
            except Exception as e:
                self.logger.debug("Realtime lookup failed for %s: %s", code, e)
                profile["realtime"] = self._get_stock_from_cache(code, market_code)
        else:
            profile["realtime"] = self._get_stock_from_cache(code, market_code)

        if profile["realtime"]:
            profile["name"] = profile.get("name") or profile["realtime"].get("name") or ""
            profile["industry"] = profile.get("industry") or profile["realtime"].get("industry") or ""

        indicators: dict[str, Any] = {}
        try:
            history = self.get_history(code, market_code, start="2000-01-01", end="2099-12-31")
            if history and self._indicator_provider:
                if hasattr(self._indicator_provider, 'calculate'):
                    indicators = self._indicator_provider.calculate(history)
        except Exception as e:
            self.logger.debug(f"Indicator calculation failed: {e}")

        return StockDetailResult(code=code, market=market_label, profile=profile, indicators=indicators)

    def _get_stock_from_cache(self, code: str, market) -> GenericResponseDTO:
        """Get stock data from cache as fallback."""
        try:
            if self._stock_cache is None:
                return {}
            cached = self._stock_cache.get_stocks_by_codes([code])
            target6 = _code6(code)
            for s in cached:
                c = s.get("code", "")
                if code in c or c in code or _code6(c) == target6:
                    return {
                        "code": code,
                        "name": s.get("name", code),
                        "price": float(s.get("price", 0) or 0),
                        "change_amount": float(s.get("change", s.get("change_amount", 0)) or 0),
                        "change_pct": float(s.get("change_pct", 0) or 0),
                        "volume": float(s.get("volume", 0) or 0),
                        "amount": float(s.get("amount", 0) or 0),
                        "turnover": float(s.get("turnover", 0) or 0),
                        "pe": float(s.get("pe", 0) or 0) or None,
                        "pb": float(s.get("pb", 0) or 0) or None,
                        "total_market_cap": float(s.get("total_market_cap", s.get("market_cap", 0)) or 0),
                        "industry": s.get("industry", "") or "",
                    }
        except Exception as e:
            self.logger.debug(f"Cache fallback failed for {code}: {e}")
        return {}

    def get_indicators(self, history: list[dict[str, Any]]) -> GenericResponseDTO:
        """Calculate technical indicators using the injected provider."""
        if not self._indicator_provider:
            return {}
        return self._indicator_provider.calculate(history)
    
    def search_stocks(
        self,
        query: str,
        *,
        limit: int = 20,
        market: str | MarketCode | None = "CN",
    ) -> list[dict[str, Any]]:
        """Search local stock cache by name/code substring (CN-only fallback)."""
        if not query or not query.strip():
            return []
        market_code = _resolve_market_code(market or "CN")
        if market_code != MarketCode.CN:
            return []
        if self._stock_cache is None:
            return []
        try:
            all_stocks = self._stock_cache.get_all_stocks(max_age_minutes=60 * 24 * 30) or []
        except Exception as exc:
            self.logger.warning("search_stocks cache lookup failed: %s", exc)
            return []

        q = query.strip().lower()
        results: list[dict[str, Any]] = []
        for s in all_stocks:
            code = str(s.get("code") or "")
            name = str(s.get("name") or "").lower()
            if q in code or q in name:
                results.append({
                    "symbol": code,
                    "name": s.get("name", code),
                    "market": market_code.value,
                    "price": float(s.get("price", 0) or 0),
                    "change_pct": float(s.get("change_pct", 0) or 0),
                    "industry": s.get("industry", "") or "",
                })
                if len(results) >= limit:
                    break
        return results

    def list_quotes(
        self, market: str | MarketCode, symbols: list[str] | None = None
    ) -> list[dict[str, Any]]:
        """List market quotes as dict rows for watchlist / workbench consumers."""
        if not self._market_provider:
            logger.warning("list_quotes: no market_provider configured")
            return []
        if not symbols:
            return []
        market_code = _resolve_market_code(market)
        try:
            lookup = (
                [SymbolNormalizer().normalize(s) for s in symbols]
                if market_code == MarketCode.CN
                else [str(s).strip() for s in symbols]
            )
            raw: list[object] = []
            if hasattr(self._market_provider, "get_realtime_quotes"):
                raw = self._market_provider.get_realtime_quotes(lookup, market_code) or []
            elif hasattr(self._market_provider, "get_quotes"):
                result = self._market_provider.get_quotes(lookup, market_code)
                raw = list(result.values()) if isinstance(result, dict) else (result or [])

            by_code6: dict[str, dict[str, Any]] = {}
            for item in raw:
                if isinstance(item, dict):
                    row = dict(item)
                    sym = str(row.get("code") or "")
                else:
                    sym = str(getattr(item, "code", "") or "")
                    row = _quote_to_realtime(sym, item)
                code6 = _code6(str(row.get("code") or sym))
                if not code6:
                    continue
                row["code"] = code6
                by_code6[code6] = row

            rows: list[dict[str, Any]] = []
            for sym in symbols:
                code6 = _code6(sym)
                row = by_code6.get(code6)
                if row:
                    rows.append(row)
                else:
                    rows.append({"code": code6 or sym, "name": sym, "price": 0.0, "change_pct": 0.0})
            return rows
        except Exception as e:
            logger.error("Error listing quotes: %s", e)
            return []

    def get_panorama(self, market: str) -> GenericResponseDTO[str, object]:
        """Get market panorama."""
        if not self._market_provider:
            return {"market": market, "status": "active", "trend": "neutral", "indices": {}}
        try:
            if hasattr(self._market_provider, 'get_panorama'):
                return self._market_provider.get_panorama(market)
        except Exception as e:
            logger.error(f"Error getting panorama: {e}")
        return {"market": market, "status": "active", "trend": "neutral", "indices": {}}

    def get_sentiment(self, market: str) -> GenericResponseDTO[str, object]:
        """Get market sentiment."""
        return {"market": market, "score": 0.5, "label": "neutral"}

    def get_history(self, symbol: str, market: object, start: str, end: str) -> list:
        """Get history data as list of dicts (for backward compatibility)."""
        self.logger.info(f"get_history called: {symbol}, {market}, {start}-{end}")
        market_str = market.value if hasattr(market, 'value') else str(market)

        from app.domain.enums import MarketCode
        from app.domain.shared.market_history_utils import filter_sort_history

        m_enum = market if isinstance(market, MarketCode) else MarketCode(
            market_str.upper() if market_str else "CN"
        )

        if m_enum == MarketCode.CN:
            try:
                from app.config import get_settings

                if get_settings().use_mysql and self._market_provider and hasattr(
                    self._market_provider, "get_stock_history"
                ):
                    result = self._market_provider.get_stock_history(symbol, m_enum, start, end)
                    if result:
                        self.logger.info(
                            "get_history: %d bars from market_provider (MySQL-first CN)",
                            len(result),
                        )
                        return filter_sort_history(result, start, end)
            except Exception as e:
                self.logger.warning("CN MySQL-first history failed: %s", e)

        if self._stock_cache:
            try:
                from app.domain.enums import MarketCode
                from app.domain.shared.symbol_normalizer import SymbolNormalizer

                m_enum = market if isinstance(market, MarketCode) else MarketCode(market_str.upper() if market_str else "CN")
                cache_key = (
                    SymbolNormalizer.to_db_code(symbol)
                    if m_enum == MarketCode.CN
                    else f"{market_str}:{symbol}"
                )
                cached = self._stock_cache.get_stock_history_for_code(cache_key, limit=5000)
                if cached:
                    self.logger.info(f"Got {len(cached)} bars from stock_cache")
                    return filter_sort_history(cached, start, end)
            except Exception as e:
                self.logger.warning(f"Cache lookup failed: {e}")
        
        if self._market_provider and hasattr(self._market_provider, "get_stock_history"):
            try:
                from app.domain.enums import MarketCode
                m = market if isinstance(market, MarketCode) else MarketCode(market_str.upper() if market_str else "CN")
                result = self._market_provider.get_stock_history(symbol, m, start, end)
                self.logger.info(f"market_provider returned {len(result) if result else 0} bars")
                return result
            except Exception as e:
                self.logger.error(f"market_provider get_stock_history failed: {e}", exc_info=True)

        self.logger.warning(f"get_history: no data for {symbol}")
        return []

    def get_bars_between(self, code: str, market: object, start: str, end: str) -> list[BarData]:
        """Get bars between dates - returns typed BarData list."""
        raw = self.get_history(code, market, start, end)
        from app.domain.dto.bar_data_factory import history_rows_to_bar_data_list
        return history_rows_to_bar_data_list(raw)

    def get_news_snapshot(self, symbol: str, market: object) -> list:
        """Get news snapshot."""
        if not self._news_provider:
            return []
        try:
            if hasattr(self._news_provider, 'get_news'):
                return self._news_provider.get_news(symbol, market)
        except Exception as e:
            logger.error(f"Error getting news snapshot: {e}")
        return []


__all__ = ["StockApplicationService", "StockDetailResult"]