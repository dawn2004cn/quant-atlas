from __future__ import annotations

from app.domain.dto.service_result import GenericResponseDTO

"""Market Services - Market data services.

This module provides market-related services:
- MarketService: Market data operations (with async support)
"""

from datetime import datetime, timedelta

from app.application.dto.market_data_dto import StockQuoteDTO as MarketQuoteDTO
from app.core.base_service import BaseApplicationService
from app.core.logger import get_logger
from app.domain.dto.market_data_dto import PanoramaDTO
from app.domain.dto.quote_factory import canonical_quote_payload, panorama_row_to_quote_dto
from app.domain.enums import MarketCode
from app.domain.ports.cache_port import CachePort
from app.domain.ports.stock_cache_port import StockCachePort
from app.modules.system.services.async_mixin import AsyncServiceMixin
from app.modules.system.services.helpers.quote_cache_wiring import get_quote_cache_port

logger = get_logger(__name__)

# A-share full-market snapshot should contain thousands of symbols; partial cache must refresh.
_CN_FULL_MARKET_MIN_ROWS = 1500

# Liquid A-shares for panorama / homepage when AkShare is unavailable (Tencent path).
_CN_PAGE_UNIVERSE = (
    "600519", "601318", "000001", "000858", "600036", "300750", "601166", "600276",
    "002594", "002415", "601888", "000333", "600900", "601398", "000651", "600030",
    "000002", "601088", "000725", "601628", "601169", "002352", "600016", "601988",
    "600000", "601328", "601288", "601857", "601601", "600887", "000568", "002304",
    "300059", "002475", "002230", "000063", "002714", "300124", "601012", "600438",
    "300274", "002371", "688981", "688111", "600809", "000596", "002142", "601668",
    "601800", "600048", "601186", "000166", "600104", "601633", "002027", "300498",
)

class MarketApplicationService(BaseApplicationService, AsyncServiceMixin):
    """Market data service with async support."""

    def __init__(
        self,
        market_provider: object | None = None,
        industry_provider: object | None = None,
        stock_cache: StockCachePort | None = None,
        cache: CachePort | None = None,
    ):
        super().__init__()
        self._market_provider = market_provider
        self._industry_provider = industry_provider
        self._stock_cache = stock_cache
        self.cache = get_quote_cache_port()
        self._cache = cache  # generic cache port for get_panorama etc.
        self._async_provider = None
        self.logger.info("MarketApplicationService initialized")

    @property
    def async_provider(self):
        """Lazy-load async provider wrapper."""
        if self._async_provider is None:
            from app.modules.system.services.helpers.async_market_access import wrap_market_provider_for_async
            self._async_provider = wrap_market_provider_for_async(self._market_provider)
        return self._async_provider

    async def get_quote_async(self, code: str) -> GenericResponseDTO:
        """Get real-time quote asynchronously."""
        try:
            return await self.async_provider.get_realtime_quotes([code], MarketCode.CN)
        except Exception as e:
            self.logger.error(f"Error getting quote for {code}: {e}")
            return {}

    async def get_quotes_async(self, codes: list[str]) -> GenericResponseDTO:
        """Get multiple quotes asynchronously."""
        try:
            quotes = await self.async_provider.get_realtime_quotes(codes, MarketCode.CN)
            return {q.get('code') or q.get('symbol'): q for q in quotes}
        except Exception as e:
            self.logger.error(f"Error getting quotes: {e}")
            return {}

    async def get_market_overview_async(self, market: MarketCode) -> GenericResponseDTO:
        """Get market overview asynchronously."""
        try:
            return await self.async_provider.get_market_overview(market)
        except Exception as e:
            self.logger.error(f"Error getting market overview: {e}")
            return {}

    def get_quote(self, code: str) -> GenericResponseDTO[str, object]:
        """Get real-time quote."""
        try:
            return self._market_provider.get_quote(code)
        except Exception as e:
            self.logger.error(f"Error getting quote for {code}: {e}")
            return {}

    def get_quotes(self, codes: list[str]) -> GenericResponseDTO[str, object]:
        """Get multiple quotes with robust normalization."""
        cached = self.cache.get_quotes(codes)
        missing = [c for c in codes if c not in cached]

        if not missing:
            return cached

        fresh = {}
        try:
            raw_results = []
            if hasattr(self._market_provider, 'get_realtime_quotes'):
                raw_results = self._market_provider.get_realtime_quotes(missing, MarketCode.CN)
            elif hasattr(self._market_provider, 'get_quotes'):
                raw_results = self._market_provider.get_quotes(missing)

            # Robust normalization
            if isinstance(raw_results, list):
                for item in raw_results:
                    symbol = getattr(item, 'symbol', None) or getattr(item, 'code', None) or (item.get('code') if isinstance(item, dict) else None)
                    if symbol:
                        if hasattr(item, '__dict__'):
                            payload = {k: v for k, v in vars(item).items() if not str(k).startswith("_")}
                        elif hasattr(item, 'to_dict'):
                            payload = item.to_dict()
                        elif isinstance(item, dict):
                            payload = item
                        else:
                            payload = {"code": symbol}
                        code6 = "".join(ch for ch in str(symbol) if ch.isdigit())[-6:].zfill(6)
                        fresh[str(symbol)] = payload
                        if code6 and code6 != "000000":
                            fresh[code6] = payload
            elif isinstance(raw_results, dict):
                fresh = raw_results
                for key, payload in list(raw_results.items()):
                    symbol = key
                    if isinstance(payload, dict):
                        symbol = payload.get("code") or payload.get("symbol") or key
                    code6 = "".join(ch for ch in str(symbol) if ch.isdigit())[-6:].zfill(6)
                    if code6 and code6 != "000000":
                        fresh[code6] = payload

            if fresh:
                self.cache.set_quotes(fresh)
        except Exception as e:
            self.logger.error(f"Error fetching quotes: {e}")

        return {**cached, **fresh}

    def _fetch_fresh_quotes_dict(self, codes: list[str]) -> dict[str, object]:
        """Fetch missing quotes; optional async path when ``ENABLE_ASYNC_MARKET_QUOTES=1``."""
        from app.modules.market_data.services.quote_fetch_policy import async_market_quotes_enabled

        if async_market_quotes_enabled():
            from app.application.request_executor import run_async

            async_result = run_async(self.get_quotes_async(codes))
            if isinstance(async_result, dict) and async_result:
                self.logger.debug("list_quotes: async fetch returned %s symbols", len(async_result))
                return async_result
        return self.get_quotes(codes)

    def _serialize_stock(self, s: dict | object) -> GenericResponseDTO[str, object]:
        """Serialize stock data for QuoteDTO."""
        if not s:
            return {}
        if not isinstance(s, dict):
            if hasattr(s, "__dict__"):
                s = {k: v for k, v in vars(s).items() if not str(k).startswith("_")}
            elif hasattr(s, "model_dump"):
                s = s.model_dump()
            else:
                return {}
        code = s.get("code", s.get("symbol", ""))
        code6 = "".join(ch for ch in str(code) if ch.isdigit())[-6:].zfill(6)
        return canonical_quote_payload(
            {
                "code": code6,
                "name": s.get("name", ""),
                "industry": s.get("industry", ""),
                "price": float(s.get("price", 0) or 0),
                "change_amount": float(s.get("change", s.get("change_amount", 0)) or 0),
                "change_pct": float(s.get("change_pct", s.get("pct_chg", 0)) or 0),
                "volume": int(float(s.get("volume", 0) or 0)),
                "amount": float(s.get("amount", 0) or 0),
                "turnover": float(s.get("turnover", 0) or 0),
                "volume_ratio": float(s.get("volume_ratio", 0) or 0),
                "amplitude": float(s.get("amplitude", 0) or 0),
                "pe": float(s.get("pe", 0) or 0),
                "pb": float(s.get("pb", 0) or 0),
            },
            market="CN",
        )

    def _dedup_stocks(self, stocks: list[dict]) -> list[dict]:
        """Deduplicate stocks by 6-digit code, keeping the newest."""
        seen = {}
        for s in stocks:
            code = s.get("code", "")
            code6 = "".join(ch for ch in str(code) if ch.isdigit())[-6:].zfill(6)
            if not code6 or code6 in ("000000", "999999"):
                continue
            update_time = s.get("update_time", "")
            if code6 not in seen or update_time > seen[code6].get("_update_time", ""):
                s_copy = dict(s)
                s_copy["_code6"] = code6
                seen[code6] = s_copy
        result = list(seen.values())
        result.sort(key=lambda x: x.get("price", 0), reverse=True)
        return result

    def list_quotes(
        self,
        market: MarketCode,
        symbols: list[str] | None = None,
        *,
        live: bool = True,
    ) -> list[dict]:
        """Get quotes for a market. Uses cache or fetches from provider."""
        cache = self._stock_cache
        if cache is None:
            self.logger.warning("list_quotes: stock_cache not configured")
            return []

        try:
            self.logger.info(f"list_quotes: market={market}, symbols_count={len(symbols) if symbols else 0}")

            if market == MarketCode.CN:
                return self._list_cn_quotes(market, symbols, cache, live=live)

            if not symbols:
                stocks = cache.get_all_stocks(max_age_minutes=10080)
                self.logger.info(f"Cache returned {len(stocks)} stocks")
                deduped = self._dedup_stocks(stocks)
                return [self._serialize_stock(s) for s in deduped]

            all_stocks = []
            chunk_size = 500
            for i in range(0, len(symbols), chunk_size):
                chunk = symbols[i:i + chunk_size]
                all_stocks.extend(cache.get_stocks_by_codes(chunk))

            self.logger.info(f"Loaded {len(all_stocks)} stocks for {len(symbols)} requested symbols")

            if not all_stocks and symbols:
                quotes_dict = self.get_quotes(self._normalize_cn_symbols(symbols[:100]))
                return [self._serialize_stock(v) for v in quotes_dict.values()]

            deduped = self._dedup_stocks(all_stocks)
            return [self._serialize_stock(s) for s in deduped]
        except Exception as e:
            self.logger.error(f"list_quotes failed: {e}", exc_info=True)
            return []

    def list_quotes_tencent(
        self,
        symbols: list[str] | None = None,
        *,
        max_symbols: int | None = None,
    ) -> list[dict]:
        """Fetch CN quotes via Tencent only. Never imports or calls AkShare."""
        if symbols:
            limited = symbols[: max(0, int(max_symbols))] if max_symbols is not None else symbols
            return self.list_quotes(MarketCode.CN, limited)
        cache = self._stock_cache
        try:
            return self._pull_cn_via_tencent_batches(
                cache, allow_akshare=False, max_symbols=max_symbols
            )
        except Exception as exc:
            self.logger.warning("list_quotes_tencent failed: %s", exc)
            return []

    def _list_cn_quotes(
        self,
        market: MarketCode,
        symbols: list[str] | None,
        cache,
        *,
        live: bool = True,
    ) -> list[dict]:
        """Fetch CN market quotes using cache, with live provider fallback."""
        if not symbols:
            all_stocks = cache.get_all_stocks(max_age_minutes=10080)
            if all_stocks:
                deduped = self._dedup_stocks(all_stocks)
                serialized = [self._serialize_stock(s) for s in deduped]
                if not live or len(serialized) >= _CN_FULL_MARKET_MIN_ROWS:
                    self.logger.info(
                        "list_quotes CN full market: %s rows from stock_cache",
                        len(serialized),
                    )
                    return serialized
                self.logger.info(
                    "list_quotes CN cache partial (%s rows), refreshing live snapshot",
                    len(serialized),
                )
            elif not live:
                return []

        if symbols:
            normalized = self._normalize_cn_symbols(symbols)
            all_stocks: list[dict] = []
            chunk_size = 500
            for i in range(0, len(normalized), chunk_size):
                chunk = normalized[i:i + chunk_size]
                all_stocks.extend(cache.get_stocks_by_codes(chunk))

            by_code6: dict[str, dict] = {}
            stale_cutoff = (datetime.now() - timedelta(hours=4)).strftime("%Y-%m-%d %H:%M:%S")
            for row in all_stocks:
                update_time = str(row.get("update_time") or "")
                if update_time < stale_cutoff:
                    continue
                ser = self._serialize_stock(row)
                canonical = str(ser.get("code") or "")
                code6 = str(ser.get("code6") or "".join(ch for ch in canonical if ch.isdigit())[-6:].zfill(6))
                if canonical:
                    by_code6[canonical] = ser
                if code6 and code6 != "000000":
                    by_code6[code6] = ser

            missing = []
            for sym in symbols:
                code6 = "".join(ch for ch in str(sym) if ch.isdigit())[-6:].zfill(6)
                if code6 and code6 not in by_code6:
                    missing.append(sym)

            if missing:
                fresh = self._fetch_fresh_quotes_dict(self._normalize_cn_symbols(missing))
                fresh_stocks = []
                for item in fresh.values():
                    ser = self._serialize_stock(item)
                    canonical = str(ser.get("code") or "")
                    code6 = str(ser.get("code6") or "".join(ch for ch in canonical if ch.isdigit())[-6:].zfill(6))
                    if canonical:
                        by_code6[canonical] = ser
                    if code6 and code6 != "000000":
                        by_code6[code6] = ser
                        fresh_stocks.append({
                            "code": canonical or code6,
                            "name": item.get("name", ""),
                            "price": float(item.get("price", 0) or 0),
                            "change_pct": float(item.get("change_pct", 0) or 0),
                            "change_amount": float(item.get("change_amount", item.get("change", 0)) or 0),
                            "prev_close": float(item.get("prev_close", 0) or 0),
                            "volume": float(item.get("volume", 0) or 0),
                            "amount": float(item.get("amount", 0) or 0),
                            "turnover": float(item.get("turnover", 0) or 0),
                            "volume_ratio": float(item.get("volume_ratio", 0) or 0),
                            "amplitude": float(item.get("amplitude", 0) or 0),
                            "pe": float(item.get("pe", 0) or 0),
                            "pb": float(item.get("pb", 0) or 0),
                            "total_market_cap": float(item.get("total_market_cap", 0) or 0),
                            "industry": str(item.get("industry", "") or ""),
                        })
                if fresh_stocks:
                    try:
                        cache.save_stocks(fresh_stocks)
                        self.logger.info("Saved %d fresh stocks to cache from Tencent", len(fresh_stocks))
                    except Exception as exc:
                        self.logger.debug("Failed to save fresh stocks to cache: %s", exc)

            ordered: list[dict] = []
            for sym in symbols:
                code6 = "".join(ch for ch in str(sym) if ch.isdigit())[-6:].zfill(6)
                if code6 in by_code6:
                    ordered.append(by_code6[code6])
            return ordered

        return self._fetch_live_cn_snapshot(cache)

    def _pull_akshare_cn_spot(self, cache) -> list[dict]:
        """Fetch full A-share snapshot from AkShare and persist to stock cache."""
        try:
            import akshare as ak

            df = ak.stock_zh_a_spot_em()
            if df is None or df.empty:
                return []
            stocks: list[dict] = []
            for _, row in df.iterrows():
                try:
                    stocks.append(
                        {
                            "code": str(row.get("代码", row.get("symbol", ""))),
                            "name": str(row.get("名称", row.get("name", ""))),
                            "price": float(row.get("最新价", row.get("price", 0)) or 0),
                            "change_amount": float(row.get("涨跌额", row.get("change", 0)) or 0),
                            "change_pct": float(row.get("涨跌幅", row.get("change_pct", 0)) or 0),
                            "volume": float(row.get("成交量", row.get("volume", 0)) or 0),
                            "amount": float(row.get("成交额", row.get("amount", 0)) or 0),
                            "industry": str(row.get("所属行业", "")) or "",
                        }
                    )
                except (ValueError, TypeError):
                    continue
            if not stocks:
                return []
            cache.save_stocks(stocks)
            self.logger.info("Fetched %s stocks from akshare", len(stocks))
            deduped = self._dedup_stocks(stocks)
            return [self._serialize_stock(s) for s in deduped][:5000]
        except Exception as exc:
            self.logger.warning("akshare fetch failed: %s", exc)
            return []

    def _fetch_cn_universe_codes(
        self,
        cache,
        *,
        allow_akshare: bool = True,
        max_symbols: int | None = None,
    ) -> list[str]:
        """Resolve the CN symbol universe for batched Tencent refresh."""
        seen: set[str] = set()
        codes: list[str] = []

        def _add(raw: object) -> None:
            code6 = "".join(ch for ch in str(raw or "") if ch.isdigit())[-6:].zfill(6)
            if code6 and code6 != "000000" and code6 not in seen:
                seen.add(code6)
                codes.append(code6)

        if not allow_akshare:
            for seed in _CN_PAGE_UNIVERSE:
                _add(seed)

        if cache is not None:
            try:
                for code in cache.list_all_codes() or []:
                    _add(code)
            except Exception as exc:
                self.logger.warning("CN universe via cache.list_all_codes failed: %s", exc)

        if allow_akshare:
            for seed in _CN_PAGE_UNIVERSE:
                _add(seed)
            if len(codes) < _CN_FULL_MARKET_MIN_ROWS:
                try:
                    import akshare as ak

                    df = ak.stock_info_a_code_name()
                    if df is not None and not df.empty:
                        code_col = "code" if "code" in df.columns else df.columns[0]
                        for code in df[code_col].tolist():
                            _add(code)
                except Exception as exc:
                    self.logger.warning("CN universe via stock_info_a_code_name failed: %s", exc)

        if max_symbols is not None:
            return codes[: max(0, int(max_symbols))]
        return codes

    def _pull_cn_via_tencent_batches(
        self,
        cache,
        *,
        allow_akshare: bool = True,
        max_symbols: int | None = None,
    ) -> list[dict]:
        """Batch-fetch CN quotes via Tencent gateway when AkShare snapshot is unavailable."""
        codes = self._fetch_cn_universe_codes(
            cache, allow_akshare=allow_akshare, max_symbols=max_symbols
        )
        if not codes:
            return []

        merged: dict[str, dict] = {}
        batch_size = 400
        for offset in range(0, len(codes), batch_size):
            chunk = codes[offset : offset + batch_size]
            try:
                fresh = self._fetch_fresh_quotes_dict(self._normalize_cn_symbols(chunk))
            except Exception as exc:
                self.logger.warning(
                    "Tencent batch %s-%s failed: %s",
                    offset,
                    offset + len(chunk),
                    exc,
                )
                continue
            for payload in fresh.values():
                if not isinstance(payload, dict):
                    continue
                ser = self._serialize_stock(payload)
                code6 = str(ser.get("code") or "").strip()
                if not code6:
                    continue
                merged[code6] = {
                    "code": code6,
                    "name": ser.get("name") or payload.get("name", ""),
                    "price": ser.get("price", 0),
                    "change_pct": ser.get("change_pct", 0),
                    "change_amount": ser.get("change_amount", 0),
                    "volume": ser.get("volume", 0),
                    "amount": ser.get("amount", 0),
                    "turnover": ser.get("turnover", 0),
                    "volume_ratio": ser.get("volume_ratio", 0),
                    "amplitude": ser.get("amplitude", 0),
                    "pe": ser.get("pe", 0),
                    "pb": ser.get("pb", 0),
                    "industry": ser.get("industry") or payload.get("industry", ""),
                }

        if not merged:
            return []

        stocks = list(merged.values())
        try:
            cache.save_stocks(stocks)
            self.logger.info("Saved %s stocks from Tencent batch refresh", len(stocks))
        except Exception as exc:
            self.logger.debug("save_stocks after Tencent refresh failed: %s", exc)

        return [self._serialize_stock(s) for s in self._dedup_stocks(stocks)]

    def _fetch_live_cn_snapshot(self, cache) -> list[dict]:
        """Refresh CN full-market snapshot: AkShare first, then Tencent batches, then cache."""
        ak_rows = self._pull_akshare_cn_spot(cache)
        if len(ak_rows) >= _CN_FULL_MARKET_MIN_ROWS:
            return ak_rows

        tencent_rows = self._pull_cn_via_tencent_batches(cache)
        if len(tencent_rows) >= _CN_FULL_MARKET_MIN_ROWS:
            self.logger.info(
                "list_quotes CN full market: %s rows from Tencent batches",
                len(tencent_rows),
            )
            return tencent_rows

        if ak_rows:
            return ak_rows
        if tencent_rows:
            return tencent_rows

        all_stocks = cache.get_all_stocks(max_age_minutes=10080)
        self.logger.info("Cache returned %s stocks (live refresh unavailable)", len(all_stocks))
        deduped = self._dedup_stocks(all_stocks)
        return [self._serialize_stock(s) for s in deduped]

    def _normalize_cn_symbols(self, symbols: list[str]) -> list[str]:
        """Convert symbols to 'sh600519' format, matching SymbolNormalizer rules."""
        result = []
        for s in symbols:
            s = s.strip()
            if not s:
                continue
            if s.startswith(("sh", "sz", "bj", "SH", "SZ", "BJ")):
                result.append(s.lower())
            elif s.startswith("6"):
                result.append(f"sh{s}")
            elif s.startswith(("0", "3")):
                result.append(f"sz{s}")
            elif s.startswith(("8", "4", "9")):
                result.append(f"bj{s}")
            else:
                result.append(f"sz{s}")
        return result

    def get_quotes_dto(self, codes: list[str]) -> list[MarketQuoteDTO]:
        """Get quotes as DTOs."""
        quotes = self.get_quotes(codes)
        return [
            MarketQuoteDTO(
                code=code,
                name=quotes.get(code, {}).get('name', ''),
                price=quotes.get(code, {}).get('price', 0),
                change_pct=quotes.get(code, {}).get('change_pct', 0),
                volume=quotes.get(code, {}).get('volume', 0),
                amount=quotes.get(code, {}).get('amount', 0),
            )
            for code in codes
        ]

    def get_panorama(self, market: MarketCode | str) -> PanoramaDTO:
        """Get market panorama summary including rankings."""
        m = market if isinstance(market, MarketCode) else (MarketCode.CN if str(market).upper() == "CN" else MarketCode.HK)
        from app.core.runtime_config import get_runtime_int

        ttl = get_runtime_int("MARKET_PANORAMA_CACHE_TTL", 45)
        cache_key = f"market:panorama:{m.value}"
        cache = self._cache  # uses injected CachePort or falls back to no-op

        def _build() -> dict[str, object]:
            return self._build_panorama(m).model_dump()

        if cache is not None:
            payload = cache.get_or_set(cache_key, _build, ttl=ttl)
        else:
            payload = _build()
        return PanoramaDTO.model_validate(payload)

    def _build_panorama(self, m: MarketCode) -> PanoramaDTO:
        self.logger.info("get_panorama: market=%s", m)
        overview = {"market_status": "active", "sentiment_score": 0.0}
        rankings: dict = {}
        try:
            if hasattr(self._market_provider, "get_market_overview"):
                overview.update(self._market_provider.get_market_overview(m))
            if hasattr(self._market_provider, "get_market_rankings"):
                rankings.update(self._market_provider.get_market_rankings(m))
        except Exception as e:
            self.logger.error("Error getting market panorama: %s", e, exc_info=True)
        return PanoramaDTO(
            market_status=overview.get("market_status", "active"),
            sentiment_score=float(overview.get("sentiment_score", 0.0)),
            gainers=[panorama_row_to_quote_dto(q, market=m.value) for q in rankings.get("gainers", [])],
            losers=[panorama_row_to_quote_dto(q, market=m.value) for q in rankings.get("losers", [])],
            amounts=[panorama_row_to_quote_dto(q, market=m.value) for q in rankings.get("amounts", [])],
            turnovers=[panorama_row_to_quote_dto(q, market=m.value) for q in rankings.get("turnovers", [])],
        )

    def _sentiment_is_stale(self, update_time: object) -> bool:
        if not update_time:
            return True
        try:
            from datetime import datetime, timezone

            if isinstance(update_time, str):
                dt = datetime.fromisoformat(update_time.replace("Z", "+00:00"))
            else:
                dt = update_time
            if getattr(dt, "tzinfo", None) is None:
                dt = dt.replace(tzinfo=timezone.utc)
            now = datetime.now(timezone.utc)
            return now - dt.astimezone(timezone.utc) >= timedelta(minutes=30)
        except Exception as exc:
            logger.warning("market_service.py._sentiment_is_stale: %s", exc)
            return True

    def _build_sentiment_payload(
        self,
        m_str: str,
        up: int,
        down: int,
        flat: int,
        *,
        stale: bool,
        last_update: object = None,
        prefix: str = "全市场",
    ) -> dict[str, object]:
        total = up + down + flat
        score = (up / total * 100) if total > 0 else 50
        normalized_update = last_update
        if normalized_update is not None and hasattr(normalized_update, "isoformat"):
            normalized_update = normalized_update.isoformat()
        return {
            "market": m_str,
            "score": score,
            "level": "看多" if score > 60 else ("看空" if score < 40 else "中性"),
            "emoji": "🚀" if score > 60 else ("📉" if score < 40 else "⚖️"),
            "description": (
                f"{prefix}上涨 {up} 家，下跌 {down} 家，平盘 {flat} 家（共 {total} 只）。"
            ),
            "stale": stale,
            "last_update": normalized_update,
            "stats": {
                "gainers": up,
                "losers": down,
                "neutral": flat,
                "total": total,
            },
        }

    def _fetch_cn_market_breadth(self) -> tuple[int, int, int] | None:
        """Count A-share up/down/flat from AkShare full spot board."""
        try:
            import akshare as ak

            frame = ak.stock_zh_a_spot_em()
            if frame is None or getattr(frame, "empty", True):
                return None
            change_col = None
            for candidate in ("涨跌幅", "change_pct", "pct_chg"):
                if candidate in frame.columns:
                    change_col = candidate
                    break
            if change_col is None:
                return None

            def _to_pct(value: object) -> float:
                try:
                    if value is None or str(value).strip() in ("", "-", "nan"):
                        return 0.0
                    return float(value)
                except (TypeError, ValueError):
                    return 0.0

            changes = frame[change_col].map(_to_pct)
            up = int((changes > 0).sum())
            down = int((changes < 0).sum())
            flat = int(len(changes) - up - down)
            if up + down + flat < _CN_FULL_MARKET_MIN_ROWS:
                return None
            return up, down, flat
        except Exception as exc:
            self.logger.warning("CN market breadth fetch failed: %s", exc)
            return None

    def _persist_sentiment_cache(self, market: str, up: int, down: int, flat: int) -> None:
        if self._stock_cache is None:
            return
        try:
            self._stock_cache.save_sentiment(market, up, down, flat)
        except Exception as exc:
            self.logger.warning("save_sentiment failed: %s", exc)

    def get_sentiment(self, market: str | MarketCode) -> GenericResponseDTO[str, object]:
        """Get market sentiment with frontend-compatible keys."""
        m_str = market.value if isinstance(market, MarketCode) else str(market)
        is_cn = m_str.upper() in ("CN", "A", "ASHARE")
        try:
            if self._stock_cache is not None:
                stats = self._stock_cache.get_latest_sentiment(m_str)
                if stats:
                    up = int(stats.get("up_count", 0))
                    down = int(stats.get("down_count", 0))
                    flat = int(stats.get("flat_count", 0))
                    total = int(stats.get("total_count", 0)) or (up + down + flat)
                    update_time = stats.get("update_time")
                    is_stale = self._sentiment_is_stale(update_time)
                    sample_too_small = is_cn and total < _CN_FULL_MARKET_MIN_ROWS
                    if not sample_too_small and not is_stale:
                        return self._build_sentiment_payload(
                            m_str,
                            up,
                            down,
                            flat,
                            stale=False,
                            last_update=update_time,
                            prefix="当前市场",
                        )
        except Exception as exc:
            self.logger.warning("Could not get sentiment from cache for %s: %s", m_str, exc)

        if is_cn:
            breadth = self._fetch_cn_market_breadth()
            if breadth:
                up, down, flat = breadth
                self._persist_sentiment_cache(m_str, up, down, flat)
                return self._build_sentiment_payload(
                    m_str,
                    up,
                    down,
                    flat,
                    stale=False,
                    last_update=None,
                    prefix="全市场实时",
                )

            # Fallback: compute from local stock cache change_pct
            local_breadth = self._compute_local_breadth()
            if local_breadth:
                up, down, flat = local_breadth
                return self._build_sentiment_payload(
                    m_str, up, down, flat,
                    stale=True,
                    last_update=None,
                    prefix="本地缓存估算",
                )

        return {
            "market": m_str,
            "score": 50,
            "level": "中性",
            "emoji": "⚖️",
            "description": "涨跌家数暂不可用，请稍后刷新。",
            "stale": True,
            "last_update": None,
            "stats": {"gainers": 0, "losers": 0, "neutral": 0, "total": 0},
        }

    def _compute_local_breadth(self) -> tuple[int, int, int] | None:
        """Compute up/down/flat from local stock cache change_pct."""
        try:
            if self._stock_cache is None:
                return None
            stocks = self._stock_cache.get_all_stocks(max_age_minutes=1440)
            if not stocks:
                return None
            up = down = flat = 0
            for s in stocks:
                try:
                    pct = float(s.get("change_pct", 0) or 0)
                except (TypeError, ValueError):
                    continue
                if pct > 0:
                    up += 1
                elif pct < 0:
                    down += 1
                else:
                    flat += 1
            total = up + down + flat
            if total < 100:
                return None
            return up, down, flat
        except Exception as exc:
            self.logger.warning("Local breadth computation failed: %s", exc)
            return None

    def get_history(self, symbol: str, market: MarketCode, *, start: str, end: str) -> list[dict]:
        """Get historical bar data for a symbol."""
        try:
            provider = self._market_provider
            if not hasattr(provider, "get_stock_history"):
                self.logger.warning("market_provider has no get_stock_history method")
                return []
            return provider.get_stock_history(symbol, market, start, end)
        except Exception as e:
            self.logger.error("get_history failed for %s: %s", symbol, e)
            return []

    async def get_history_async(self, symbol: str, market: MarketCode, *, start: str, end: str) -> list[dict]:
        """Async version of get_history ? non-blocking bar retrieval."""
        import asyncio
        try:
            provider = self._market_provider
            if not hasattr(provider, "get_stock_history"):
                self.logger.warning("market_provider has no get_stock_history method")
                return []
            return await asyncio.to_thread(provider.get_stock_history, symbol, market, start, end)
        except Exception as e:
            self.logger.error("get_history_async failed for %s: %s", symbol, e)
            return []

    def get_history_bars(
        self,
        symbol: str,
        market: MarketCode,
        *,
        start_date: str | None = None,
        end_date: str | None = None,
        count: int = 100,
    ) -> list[dict]:
        """API-compatible alias used by v2 routes; delegates to ``get_history``."""
        bars = self.get_history(
            symbol,
            market,
            start=start_date or "",
            end=end_date or "",
        )
        if count and len(bars) > count:
            return bars[-count:]
        return bars

    def get_movements(self, market: str | MarketCode, top_n: int = 12) -> list[dict]:
        """Get market movements formatted for the dashboard."""
        m = market if isinstance(market, MarketCode) else (MarketCode.CN if str(market).upper() == "CN" else MarketCode.HK)
        self.logger.info(f"Market movements requested for {m}")

        try:
            if hasattr(self._market_provider, "get_market_rankings"):
                rankings = self._market_provider.get_market_rankings(m)
                gainers = rankings.get("gainers", [])
                movements = []
                for g in gainers[:top_n]:
                    change_pct = g.get("change_pct") or 0
                    movements.append({
                        "code": g.get("code"),
                        "name": g.get("name"),
                        "type": "涨幅领先",
                        "change_pct": change_pct,
                        "change": f"+{change_pct:.2f}%" if change_pct else "+0.00%"
                    })
                return movements
        except Exception as e:
            self.logger.error(f"Error getting market movements: {e}")
        return []



__all__ = ["MarketApplicationService"]

# Back-compat alias used by wiring modules
MarketService = MarketApplicationService
