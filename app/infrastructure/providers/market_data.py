from __future__ import annotations

"""Multi-market data provider with L1/L2 caching and Optimized Sentiment."""


import math
import threading
import time
from collections.abc import Callable
from dataclasses import asdict
from datetime import date, datetime, timedelta
from typing import Any

import yfinance as yf

from app.domain.dto.quote_factory import quote_to_dict
from app.domain.shared.market_history_utils import filter_sort_history as _filter_sort_history

from ...core.logger import get_logger
from ...domain.entities import ChipDistribution, StockQuote
from ...domain.enums import MarketCode
from ...domain.ports import MarketDataProvider
from ...domain.quote_gateway import QuoteGateway
from ...domain.tdx import TdxClient
from ..adapters.legacy_tdx_adapter import LegacyTdxAdapter
from ..adapters.tencent_quote_gateway import TencentQuoteGateway
from ..calendar.cn_sse_calendar import is_cn_equity_trading_day
from ..database.stock_cache_db import StockCache
from ..mappers.symbol_normalizer import SymbolNormalizer
from ..mappers.tencent_quote_mapper import _split_gtimg_fields

logger = get_logger(__name__)

_YFINANCE_COOLDOWN = 300  # 5 min
_HK_COOLDOWN = 300
_yfinance_failures: dict[str, int] = {}
_yfinance_until: dict[str, float] = {}
_hk_failures: int = 0
_hk_until: float = 0


def _cb_check(name: str, failures: dict, until: dict, threshold: int = 3) -> bool:
    """Return True if the circuit is OPEN (skip this source)."""
    return until.get(name, 0) > time.time()


def _cb_fail(name: str, failures: dict, until: dict, cooldown: float, threshold: int = 3) -> None:
    failures[name] = failures.get(name, 0) + 1
    if failures[name] >= threshold:
        until[name] = time.time() + cooldown
        logger.info(f"Circuit breaker opened for {name}, skipping {cooldown}s")


def _cb_success(name: str, failures: dict, until: dict) -> None:
    failures.pop(name, None)
    until.pop(name, None)


def _mark_market_data_degraded(reason: str) -> None:
    try:
        from app.core.middleware.degraded_context import mark_system_degraded

        mark_system_degraded(reason)
    except Exception:
        logger.warning("Suppressed exception", exc_info=True)
        pass


def _sanitize_ohlc_bar(h: dict[str, Any]) -> dict[str, Any] | None:
    """单根 K 线数值合法化，丢弃 NaN/非正收盘价等脏数据，修正 high/low 包络。"""
    raw_date = h.get("date") if h.get("date") is not None else h.get("Date")
    if raw_date is None:
        return None
    ds = str(raw_date)[:10]

    def _f(key: str, alt: str) -> float | None:
        v = h.get(key)
        if v is None:
            v = h.get(alt)
        if v is None:
            return None
        try:
            x = float(v)
        except (TypeError, ValueError):
            return None
        if not math.isfinite(x):
            return None
        return x

    c = _f("close", "Close")
    if c is None or c <= 0:
        return None
    o = _f("open", "Open")
    hi = _f("high", "High")
    lo = _f("low", "Low")
    if o is None or o <= 0:
        o = c
    if hi is None:
        hi = max(o, c)
    if lo is None:
        lo = min(o, c)
    hi = max(hi, o, c)
    lo = min(lo, o, c)
    if hi <= 0 or lo <= 0 or hi < lo:
        return None

    vol = _f("volume", "Volume")
    if vol is None:
        vol = _f("vol", "Vol")
    if vol is None or vol < 0:
        vol = 0.0
    amt = _f("amount", "Amount")
    if amt is None or amt < 0:
        amt = 0.0

    bar = {
        "date": ds,
        "open": o,
        "high": hi,
        "low": lo,
        "close": c,
        "volume": vol,
        "amount": amt,
        "Date": ds,
        "Open": o,
        "High": hi,
        "Low": lo,
        "Close": c,
        "Volume": vol,
        "Amount": amt,
    }
    return bar


def _finalize_history_bars(
    history: list[dict[str, Any]],
    market: MarketCode = MarketCode.CN,
) -> list[dict[str, Any]]:
    """清洗 OHLCV、剔除非交易日（A 股用 SSE 日历）、按交易日去重，升序排列。"""
    by_date: dict[str, dict[str, Any]] = {}
    for h in history:
        bar = _sanitize_ohlc_bar(h)
        if not bar:
            continue
        if market == MarketCode.CN and not is_cn_equity_trading_day(bar["date"]):
            continue
        by_date[bar["date"]] = bar
    return [by_date[k] for k in sorted(by_date)]


class MultiSourceMarketProvider(MarketDataProvider):
    """
    行情与历史 K 线：L1 内存 + L2 ``stock_cache`` SQLite；**历史 K 线读取顺序**（A 股）见
    ``get_stock_history`` 实现——默认 **SQLite → qlib_bin → 本地通达信 lday 文件**；
    通达信 TCP 与东财 AkShare 仅当对应环境开关打开时作为兜底（避免读历史走公网）。
    """

    def __init__(
        self,
        tdx_factory: Callable[[], TdxClient] | None = None,
        quote_gateway: QuoteGateway | None = None,
        cache: StockCache | None = None,
        l1_ttl_seconds: int = 60
    ):
        self._cache = cache or StockCache.default()
        self._tdx_factory = tdx_factory or LegacyTdxAdapter
        self._quote_gateway = quote_gateway or TencentQuoteGateway()
        self._tdx_adapter: TdxClient | None = None

        self._l1_cache: dict[str, tuple[StockQuote, datetime]] = {}
        self._l1_ttl = l1_ttl_seconds

        self._market_watchlists: dict[MarketCode, list[str]] = {
            MarketCode.CN: ["600519", "000001", "300750", "601318", "000858"],
            MarketCode.US: ["AAPL", "MSFT", "NVDA", "AMZN", "TSLA"],
            MarketCode.HK: ["0700.HK", "9988.HK", "3690.HK", "1810.HK", "1299.HK"],
            MarketCode.CRYPTO: ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT"],
        }

    def _get_tdx(self) -> TdxClient | None:
        if self._tdx_adapter is None:
            adapter = self._tdx_factory()
            if not adapter.is_available:
                return None
            self._tdx_adapter = adapter
        return self._tdx_adapter

    def _normalize_symbol(self, symbol: str) -> tuple[int, str]:
        code = SymbolNormalizer().normalize(symbol)
        return SymbolNormalizer.market_id(code), code

    def _cache_key(self, market: MarketCode, code: str) -> str:
        return f"{market.value}:{code}"

    def get_realtime_quotes(self, symbols: list[str] | None = None, market: MarketCode = MarketCode.CN) -> list[StockQuote]:
        if symbols:
            hit_quotes, miss_symbols = self._check_l1_cache(market, symbols)
            if not miss_symbols:
                return hit_quotes
            fresh_quotes = self._fetch_and_sync(market, miss_symbols)
            return hit_quotes + fresh_quotes
        return self._get_full_market_quotes(market)

    def get_quote(self, symbol: str, market: MarketCode = MarketCode.CN) -> StockQuote | None:
        quotes = self.get_realtime_quotes([symbol], market)
        return quotes[0] if quotes else None

    def get_quotes(self, symbols: list[str], market: MarketCode = MarketCode.CN) -> list[StockQuote]:
        return self.get_realtime_quotes(symbols, market)

    def _check_l1_cache(self, market: MarketCode, symbols: list[str]) -> tuple[list[StockQuote], list[str]]:
        hits = []
        misses = []
        now = datetime.now()
        for s in symbols:
            key = self._cache_key(market, SymbolNormalizer().normalize(s))
            if key in self._l1_cache:
                quote, ts = self._l1_cache[key]
                if (now - ts).total_seconds() < self._l1_ttl:
                    hits.append(quote)
                    continue
            misses.append(s)
        return hits, misses

    def _fetch_and_sync(self, market: MarketCode, symbols: list[str]) -> list[StockQuote]:
        if market == MarketCode.CN:
            norm_codes = [SymbolNormalizer().normalize(s) for s in symbols]
            try:
                payload = self._quote_gateway.fetch_quotes_text(norm_codes, timeout=2)
                if payload:
                    raw_lines = payload.strip().split("\n")
                    quotes = []
                    for line in raw_lines:
                        items = _split_gtimg_fields(line)
                        if len(items) < 40:
                            continue
                        code = (items[2] or "").strip()
                        if not code:
                            continue
                        from datetime import datetime
                        quotes.append(StockQuote(
                            code=code,
                            name=items[1] or code,
                            market=market,
                            price=float(items[3] or 0),
                            change_pct=float(items[32] or 0),
                            volume=float(items[6] or 0) * 100,
                            amount=float(items[37] or 0) * 10000,
                            turnover=float(items[38] or 0),
                            open_price=float(items[5] or 0),
                            high_price=float(items[33] or 0),
                            low_price=float(items[34] or 0),
                            source="tencent",
                            updated_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                            change_amount=float(items[31] or 0),
                            prev_close=float(items[4] or 0),
                            volume_ratio=float(items[64] or 0),
                            amplitude=float(items[43] or 0),
                            pe=float(items[39] or 0),
                            pb=float(items[46] or 0),
                            total_market_cap=float(items[45] or 0) * 1e8,
                            industry=self._get_industry_from_cache(code),
                        ))
                    if quotes:
                        self._update_multi_level_cache(market, quotes)
                    return quotes
                _mark_market_data_degraded("market_tencent_fallback")
                return self._get_l2_fallback(market, symbols)
            except Exception as e:
                logger.warning(f"CN quotes fetch failed, fallback to L2: {e}")
                _mark_market_data_degraded("market_tencent_fallback")
                return self._get_l2_fallback(market, symbols)

        try:
            import akshare as ak
            raw: list[dict[str, Any]] = []
            if market == MarketCode.US:
                df = ak.stock_us_spot_em()
                if df is not None and not df.empty:
                    sym_set = {s.upper() for s in symbols}
                    for _, row in df.iterrows():
                        sym = str(row.get("symbol", "")).upper()
                        if sym in sym_set:
                            raw.append(self._akrow_to_quote(dict(row), MarketCode.US))
            elif market == MarketCode.HK:
                if _hk_until > time.time():
                    logger.debug("HK circuit breaker open, skip primary")
                    _mark_market_data_degraded("market_hk_circuit")
                else:
                    try:
                        df = ak.stock_hk_spot_em()
                        _hk_failures = 0
                    except Exception as e:
                        _hk_failures += 1
                        if _hk_failures >= 3:
                            _hk_until = time.time() + _HK_COOLDOWN
                            logger.info("HK primary circuit opened for %ss", _HK_COOLDOWN)
                        logger.debug(f"HK primary failed: {e}")
                        df = None
                if df is not None and not df.empty:
                    sym_set = {s.upper() for s in symbols}
                    for _, row in df.iterrows():
                        sym = str(row.get("代码", "")).upper()
                        if sym in sym_set:
                            raw.append(self._akrow_to_quote(dict(row), MarketCode.HK))
            elif market == MarketCode.CN:
                try:
                    df = ak.stock_zh_a_spot_em()
                    if df is not None and not df.empty:
                        sym_set = {s.upper() for s in symbols}
                        for _, row in df.iterrows():
                            sym = str(row.get("代码", "")).upper()
                            if sym in sym_set:
                                raw.append(self._akrow_to_quote(dict(row), MarketCode.CN))
                except Exception as e:
                    logger.warning(f"CN AkShare fetch failed: {e}")
            elif market == MarketCode.CRYPTO:
                try:
                    df = ak.currency_latest()
                except Exception:
                    try:
                        df = ak.currency_hs_gys()
                    except Exception:
                        df = None
                if df is not None and not df.empty:
                    sym_set = {s.upper().replace("-", "") for s in symbols}
                    for _, row in df.iterrows():
                        sym = str(row.get("代码", row.get("货币对", ""))).upper().replace("-", "")
                        if sym in sym_set:
                            raw.append(self._akrow_to_quote(dict(row), MarketCode.CRYPTO))
            if raw:
                return raw
        except Exception as e:
            logger.debug(f"Non-CN quotes fetch failed for {market.value}: {e}")

        # Fallback to yfinance for US stocks
        if market == MarketCode.US:
            _mark_market_data_degraded("market_yfinance_fallback")
            return self._fetch_us_yfinance(symbols)

        # Fallback to yfinance for HK stocks
        if market == MarketCode.HK:
            _mark_market_data_degraded("market_yfinance_fallback")
            return self._fetch_hk_yfinance(symbols)

        # Fallback to yfinance for crypto
        if market == MarketCode.CRYPTO:
            _mark_market_data_degraded("market_yfinance_fallback")
            return self._fetch_crypto_yfinance(symbols)

        _mark_market_data_degraded("market_l2_cache")
        return self._get_l2_fallback(market, symbols)

    def _fetch_us_yfinance(self, symbols: list[str]) -> list[StockQuote]:
        """Use yfinance to fetch US stock quotes as fallback."""
        if _cb_check("yf_us", _yfinance_failures, _yfinance_until, 0):
            return []
        quotes = []
        for sym in symbols:
            try:
                ticker = yf.Ticker(sym)
                info = ticker.fast_info
                if info:
                    price = getattr(info, 'last_price', None) or 0
                    if price == 0:
                        price = getattr(info, 'last_close', None) or 0
                    prev = getattr(info, 'previous_close', None) or price
                    change = price - prev
                    change_pct = (change / prev * 100) if prev else 0
                    volume = getattr(info, 'last_volume', None) or 0
                    quotes.append(StockQuote(
                        code=sym.upper(),
                        name=sym,
                        price=price,
                        change_amount=change,
                        change_pct=change_pct,
                        volume=volume,
                        market=MarketCode.US,
                    ))
            except Exception as e:
                _cb_fail("yf_us", _yfinance_failures, _yfinance_until, _YFINANCE_COOLDOWN)
                logger.debug(f"yfinance fetch failed for {sym}: {e}")
                continue
            _cb_success("yf_us", _yfinance_failures, _yfinance_until)
        return quotes

    def _fetch_hk_yfinance(self, symbols: list[str]) -> list[StockQuote]:
        """Use yfinance to fetch HK stock quotes as fallback."""
        if _cb_check("yf_hk", _yfinance_failures, _yfinance_until, 0):
            return []
        quotes = []
        for sym in symbols:
            try:
                hk_sym = sym.replace(".HK", "") + ".HK"
                ticker = yf.Ticker(hk_sym)
                info = ticker.fast_info
                if info:
                    price = getattr(info, 'last_price', None) or 0
                    if price == 0:
                        price = getattr(info, 'last_close', None) or 0
                    prev = getattr(info, 'previous_close', None) or price
                    change = price - prev
                    change_pct = (change / prev * 100) if prev else 0
                    volume = getattr(info, 'last_volume', None) or 0
                    code = sym.upper().replace(".HK", "")
                    quotes.append(StockQuote(
                        code=code,
                        name=code,
                        price=price,
                        change_amount=change,
                        change_pct=change_pct,
                        volume=volume,
                        market=MarketCode.HK,
                    ))
            except Exception as e:
                _cb_fail("yf_hk", _yfinance_failures, _yfinance_until, _YFINANCE_COOLDOWN)
                logger.debug(f"yfinance fetch failed for HK {sym}: {e}")
                continue
            _cb_success("yf_hk", _yfinance_failures, _yfinance_until)
        return quotes

    def _fetch_crypto_yfinance(self, symbols: list[str]) -> list[StockQuote]:
        """Use yfinance to fetch crypto quotes as fallback."""
        if _cb_check("yf_crypto", _yfinance_failures, _yfinance_until, 0):
            return []
        quotes = []
        for sym in symbols:
            try:
                ticker = yf.Ticker(sym)
                info = ticker.fast_info
                if info:
                    price = getattr(info, 'last_price', None) or 0
                    if price == 0:
                        price = getattr(info, 'last_close', None) or 0
                    prev = getattr(info, 'previous_close', None) or price
                    change = price - prev
                    change_pct = (change / prev * 100) if prev else 0
                    volume = getattr(info, 'last_volume', None) or 0
                    quotes.append(StockQuote(
                        code=sym.upper(),
                        name=sym,
                        price=price,
                        change_amount=change,
                        change_pct=change_pct,
                        volume=volume,
                        market=MarketCode.CRYPTO,
                    ))
            except Exception as e:
                logger.debug(f"yfinance fetch failed for crypto {sym}: {e}")
        return quotes

    def _fetch_google_finance(self, symbols: list[str]) -> list[StockQuote]:
        """Use Google Finance to fetch US stock quotes as fallback."""
        if _cb_check("gf_us", _yfinance_failures, _yfinance_until, 0):
            return []

        quotes = []
        for sym in symbols:
            try:
                from app.infrastructure.providers.google_finance_provider import _get_google_finance_quotes
                gf_quotes = _get_google_finance_quotes([sym])
                quotes.extend(gf_quotes)
            except Exception as e:
                logger.debug(f"Google Finance fetch failed for {sym}: {e}")
                continue
        return quotes

    def _update_multi_level_cache(self, market: MarketCode, quotes: list[StockQuote]):
        now = datetime.now()
        l2_rows = []
        for q in quotes:
            key = self._cache_key(market, q.code)
            self._l1_cache[key] = (q, now)
            row = asdict(q)
            row["code"] = q.code
            l2_rows.append(row)
        if l2_rows:
            try:
                self._cache.save_stocks(l2_rows)
            except Exception as e:
                if "Deadlock" in str(e):
                    logger.warning(f"L2 cache sync deadlock, will retry later: {e}")
                else:
                    logger.error(f"Failed to sync L2 cache: {e}")

    def _get_industry_from_cache(self, code: str) -> str:
        """Get industry from cache for a stock code."""
        try:
            cached = self._cache.get_stocks_by_codes([code])
            for s in cached:
                c = s.get("code", "")
                if code in c or c in code:
                    return s.get("industry", "") or ""
        except Exception as e:
            logger.warning("market_data.py._get_industry_from_cache: %s", e)
        return ""

    def _get_l2_fallback(self, market: MarketCode, symbols: list[str]) -> list[StockQuote]:
        _mark_market_data_degraded("market_l2_cache")
        try:
            cached = self._cache.get_all_stocks(max_age_minutes=10080)
            norm = SymbolNormalizer()
            requested = {norm.normalize(s) for s in symbols}
            results = []
            seen = set()
            for r in cached:
                code = str(r.get("code", ""))
                code = code.split(":", 1)[1] if ":" in code else code
                if code in requested and code not in seen:
                    results.append(self._build_quote_from_cache_row(r, market))
                    seen.add(code)
            return results
        except Exception as e:
            logger.error(f"L2 fallback query failed: {e}")
            return []

    def _get_full_market_quotes(self, market: MarketCode) -> list[StockQuote]:
        try:
            rows = self._cache.get_all_stocks(max_age_minutes=10080)
            market_prefix = f"{market.value}:"
            quotes = []
            for r in rows:
                code = str(r.get("code", ""))
                if market == MarketCode.CN:
                    if code.startswith(("sh", "sz", "bj", "CN:")):
                        quotes.append(self._build_quote_from_cache_row(r, market))
                elif code.startswith(market_prefix) or code.startswith(("US:", "HK:", "CRYPTO:")):
                    quotes.append(self._build_quote_from_cache_row(r, market))

            logger.info(f"Loaded {len(quotes)} quotes for {market.value} from cache (lenient age)")

            if quotes and market == MarketCode.CN:
                top_codes = [q.code for q in quotes[:80]]
                threading.Thread(target=self._fetch_and_sync, args=(market, top_codes), daemon=True).start()
            return quotes
        except Exception as e:
            logger.error(f"Full market quote query failed: {e}")
            return []

    def _build_quote_from_cache_row(self, row: dict, market: MarketCode) -> StockQuote:
        key = str(row.get("code", ""))
        code = key.split(":", 1)[1] if ":" in key else key
        return StockQuote(
            code=code,
            name=str(row.get("name", code)),
            market=market,
            price=float(row.get("price", 0) or 0),
            change_pct=float(row.get("change_pct", 0) or 0),
            volume=float(row.get("volume", 0) or 0),
            amount=float(row.get("amount", 0) or 0),
            turnover=float(row.get("turnover", 0) or 0),
            source="cache",
            updated_at=str(row.get("update_time", "")),
            change_amount=float(row.get("change_amount", 0) or 0),
            prev_close=float(row.get("prev_close", 0) or 0),
            volume_ratio=float(row.get("volume_ratio", 0) or 0),
            amplitude=float(row.get("amplitude", 0) or 0),
            pe=float(row.get("pe", 0) or 0),
            pb=float(row.get("pb", 0) or 0),
            total_market_cap=float(row.get("total_market_cap", 0) or 0),
            industry=str(row.get("industry", "") or ""),
        )

    def _akrow_to_quote(self, row: dict, market: MarketCode) -> StockQuote:
        def _f(key: str, alt: str = "") -> float:
            v = row.get(key)
            if v is None and alt:
                v = row.get(alt)
            if v is None:
                return 0.0
            try:
                x = float(v)
            except (TypeError, ValueError):
                return 0.0
            return x

        if market == MarketCode.US:
            return StockQuote(
                code=str(row.get("symbol", "")),
                name=str(row.get("name", "")),
                market=market,
                price=_f("最新价") or _f("price"),
                change_pct=_f("涨跌幅") or _f("change_percent"),
                volume=_f("成交量") or _f("volume"),
                amount=_f("成交额") or _f("amount"),
                source="akshare_us",
                updated_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                change_amount=_f("涨跌额") or 0.0,
                prev_close=_f("昨收") or 0.0,
                open_price=_f("今开") or _f("open"),
                high_price=_f("最高") or _f("high"),
                low_price=_f("最低") or _f("low"),
            )
        elif market == MarketCode.HK:
            return StockQuote(
                code=str(row.get("代码", "")),
                name=str(row.get("名称", "")),
                market=market,
                price=_f("最新价") or _f("price"),
                change_pct=_f("涨跌幅") or _f("change_percent"),
                volume=_f("成交量") or _f("volume"),
                amount=_f("成交额") or _f("amount"),
                source="akshare_hk",
                updated_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                change_amount=_f("涨跌额") or 0.0,
                prev_close=_f("昨收") or 0.0,
                open_price=_f("今开") or _f("open"),
                high_price=_f("最高") or _f("high"),
                low_price=_f("最低") or _f("low"),
            )
        elif market == MarketCode.CN:
            return StockQuote(
                code=str(row.get("代码", "")),
                name=str(row.get("名称", "")),
                market=market,
                price=_f("最新价") or _f("price"),
                change_pct=_f("涨跌幅") or _f("change_percent"),
                volume=_f("成交量") or _f("volume"),
                amount=_f("成交额") or _f("amount"),
                source="akshare_cn",
                updated_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                change_amount=_f("涨跌额") or 0.0,
                prev_close=_f("昨收") or 0.0,
                open_price=_f("今开") or _f("open"),
                high_price=_f("最高") or _f("high"),
                low_price=_f("最低") or _f("low"),
            )
        else:
            return StockQuote(
                code=str(row.get("交易对", "")),
                name=str(row.get("名称", "")),
                market=market,
                price=_f("最新价") or _f("close"),
                change_pct=_f("涨跌幅") or 0.0,
                volume=_f("成交量") or _f("volume"),
                amount=_f("成交额") or 0.0,
                source="akshare_crypto",
                updated_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                change_amount=0.0,
                prev_close=0.0,
                open_price=_f("开盘") or 0.0,
                high_price=_f("最高") or _f("high"),
                low_price=_f("最低") or _f("low"),
            )
        key = str(row.get("code", ""))
        code = key.split(":", 1)[1] if ":" in key else key
        return StockQuote(
            code=code,
            name=str(row.get("name", code)),
            market=market,
            price=float(row.get("price", 0) or 0),
            change_pct=float(row.get("change_pct", 0) or 0),
            volume=float(row.get("volume", 0) or 0),
            amount=float(row.get("amount", 0) or 0),
            turnover=float(row.get("turnover", 0) or 0),
            source="cache",
            updated_at=str(row.get("update_time", "")),
            change_amount=float(row.get("change_amount", 0) or 0),
            prev_close=float(row.get("prev_close", 0) or 0),
            volume_ratio=float(row.get("volume_ratio", 0) or 0),
            amplitude=float(row.get("amplitude", 0) or 0),
            pe=float(row.get("pe", 0) or 0),
            pb=float(row.get("pb", 0) or 0),
            total_market_cap=float(row.get("total_market_cap", 0) or 0),
            industry=str(row.get("industry", "") or ""),
        )

    def get_stock_history(self, symbol: str, market: MarketCode, start: str, end: str) -> list[dict[str, Any]]:
        """A 股日 K - 使用多数据源适配器."""
        from .history_adapters import get_multi_source_history_provider
        from app.infrastructure.cache.history_coalesce import get_history_coalesced

        market_id, code = self._normalize_symbol(symbol)
        cache_key = self._cache_key(market, code)
        start_s, end_s = start[:10], end[:10]
        coalesce_key = f"hist:{market.value}:{code}:{start_s}:{end_s}"

        def _fetch() -> list[dict[str, Any]]:
            try:
                start_date = datetime.strptime(start_s, "%Y-%m-%d").date()
                end_date = datetime.strptime(end_s, "%Y-%m-%d").date()
            except Exception:
                from datetime import timedelta

                end_date = date.today()
                start_date = end_date - timedelta(days=365)

            provider = get_multi_source_history_provider()
            bars = provider.get_history(code, market, start_date, end_date)
            self._last_history_source = getattr(provider, "last_source", None)

            if bars:
                try:
                    self._cache.save_stock_history(cache_key, bars)
                except Exception as e:
                    logger.warning("Failed to cache history for %s (non-critical): %s", symbol, e)

            return _filter_sort_history(bars, start, end) if bars else []

        if not hasattr(self, "_last_history_source"):
            self._last_history_source = None
        return get_history_coalesced(coalesce_key, _fetch)

    def get_stock_profile(self, symbol: str, market: MarketCode) -> dict[str, Any]:
        quotes = self.get_realtime_quotes([symbol], market=market)
        if not quotes:
            return {"code": symbol, "realtime": {}}
        # asdict 会保留 MarketCode 枚举，Flask jsonify 会 500；统一走 quote_to_dict
        return {"code": symbol, "realtime": quote_to_dict(quotes[0])}

    def get_market_overview(self, market: MarketCode) -> dict[str, Any]:
        stats = self._cache.get_latest_sentiment(market.value)
        if stats:
            return {
                "market": market.value,
                "status": "success",
                "count": stats["total_count"],
                "up": stats["up_count"],
                "down": stats["down_count"],
                "flat": stats["flat_count"],
                "updated_at": stats["update_time"],
                "source": "stats_cache"
            }

        quotes = self.get_realtime_quotes(market=market)
        up = len([q for q in quotes if q.change_pct > 0])
        down = len([q for q in quotes if q.change_pct < 0])
        return {
            "market": market.value,
            "status": "success",
            "count": len(quotes),
            "up": up,
            "down": down,
            "flat": max(0, len(quotes) - up - down),
            "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "source": "live_scan"
        }

    def get_market_rankings(self, market: MarketCode) -> dict[str, list[dict[str, Any]]]:
        quotes = self.get_realtime_quotes(market=market)

        def to_dict(q: StockQuote) -> dict[str, Any]:
            return {
                "code": q.code,
                "name": q.name,
                "price": q.price,
                "change_pct": q.change_pct,
                "change_amount": q.change_amount,
                "volume": int(q.volume),
                "amount": q.amount,
                "turnover": q.turnover,
            }

        return {
            "gainers": [to_dict(r) for r in sorted(quotes, key=lambda x: x.change_pct, reverse=True)[:10]],
            "losers": [to_dict(r) for r in sorted(quotes, key=lambda x: x.change_pct)[:10]],
            "amounts": [to_dict(r) for r in sorted(quotes, key=lambda x: x.amount, reverse=True)[:10]],
            "turnovers": [to_dict(r) for r in sorted(quotes, key=lambda x: x.turnover, reverse=True)[:10]],
        }

    def get_chip_distribution(self, symbol: str, market: MarketCode) -> ChipDistribution | None:
        """从 AkShare 获取筹码分布 (移植自 DSA)。"""
        if market != MarketCode.CN:
            return None

        try:
            import akshare as ak

            # 统一代码格式，akshare 通常使用纯数字
            code = symbol.split(".")[0]
            if code.startswith("SH") or code.startswith("SZ"):
                code = code[2:]

            df = ak.stock_cyq_em(symbol=code)
            if df is None or df.empty:
                return None

            latest = df.iloc[-1]

            def safe_f(v):
                try:
                    return float(v)
                except (ValueError, TypeError):
                    return 0.0

            return ChipDistribution(
                profit_ratio=safe_f(latest.get("获利比例")),
                avg_cost=safe_f(latest.get("平均成本")),
                concentration_90=safe_f(latest.get("90集中度")),
                concentration_70=safe_f(latest.get("70集中度")),
                winner_90_low=safe_f(latest.get("90成本-低")),
                winner_90_high=safe_f(latest.get("90成本-高")),
                winner_70_low=safe_f(latest.get("70成本-低")),
                winner_70_high=safe_f(latest.get("70成本-高")),
            )
        except Exception as e:
            logger.warning(f"获取筹码分布失败 ({symbol}): {e}")
            return None

def default_history_window(days: int = 365) -> tuple[str, str]:
    end = datetime.now().date()
    start = end - timedelta(days=days)
    return start.isoformat(), end.isoformat()

